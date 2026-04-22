# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import textwrap
import threading
import unittest.mock
from datetime import datetime, timedelta, timezone

import apprise
import freezegun
import pytest
import yaml
from helpers import DESTINATIONS
from pdpyras import EventsAPISession

from cos_alerter.alerter import (
    AlerterState,
    config,
    send_test_notification,
    split_destinations,
    up_time,
)


def assert_notifications(notify_mock, add_mock, pd_mock, title, body, dedup_key):
    categorized_destinations = split_destinations(DESTINATIONS)
    add_mock.assert_has_calls(
        [unittest.mock.call(x) for x in categorized_destinations["standard"]]
    )
    notify_mock.assert_called_with(title=title, body=body)
    pd_mock.assert_called_with(source="cos-alerter", summary=body, dedup_key=dedup_key)


def test_config_gets_item(fake_fs):
    assert config["watch"]["down_interval"] == 300


def test_config_default_empty_file(fake_fs):
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write("")
    config.reload()
    assert config["watch"]["down_interval"] == 300


def test_file_not_found_error(fake_fs):
    with unittest.mock.patch("cos_alerter.alerter.logger") as mock_logger:
        os.unlink("/etc/cos-alerter.yaml")
        try:
            config.reload()
        except SystemExit as exc:
            assert exc.code == 1
            mock_logger.critical.assert_called_once_with("Config file not found. Exiting...")
        else:
            assert False


def test_duplicate_key_error(fake_fs):
    duplicate_config = """
    watch:
      down_interval: "5m"
      wait_for_first_connection: true
      clients:
        clientid1:
          key: "clientkey1"
          name: "Instance Name 1"
        clientid1:
          key: "clientkey1"
          name: "Instance Name 1"
    """
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(duplicate_config)

    try:
        config.reload()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        # If no exception is raised, fail the test
        assert False


def test_invalid_hashes(fake_fs):
    duplicate_config = """
    watch:
      down_interval: "5m"
      wait_for_first_connection: true
      clients:
        invalidhashclient:
          key: "E0E06B8DB6ED8DD4E1FFE98376E606BDF4FE4ABB4AF65BFE8B18FBFA6564D8B3"
          name: "Instance Name 1"
    """
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(duplicate_config)

    try:
        config.reload()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        # If no exception is raised, fail the test
        assert False


def test_config_default_partial_file(fake_fs):
    conf = yaml.dump({"log_level": "info"})
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(conf)
    config.reload()
    assert config["watch"]["down_interval"] == 300


def test_config_default_override(fake_fs):
    conf = yaml.dump({"watch": {"down_interval": "1m"}})
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(conf)
    config.reload()
    assert config["watch"]["down_interval"] == 60


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_initialize(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    with state:
        assert state.start_date == 1672531200.0
        assert state.start_time == 1000
        assert state.data["alert_time"] == 1000
        assert state.data["notify_time"] is None


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_up_time(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    monotonic_mock.return_value = 2000
    assert up_time() == 1000


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_is_down_from_initialize(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    with state:
        monotonic_mock.return_value = 1180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 1330  # Five and a half minutes have passed
        assert state.is_down() is True


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
@unittest.mock.patch.object(EventsAPISession, "resolve")
def test_is_down_with_reset_alert_timeout(pd_mock, monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    with state:
        monotonic_mock.return_value = 2000
        state.reset_alert_timeout()
        monotonic_mock.return_value = 2180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 2330  # Five and a half minutes have passed
        assert state.is_down() is True
        pd_mock.assert_called_with(f"{state.clientid}-None")


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_is_down_with_wait_for_first_connection(monotonic_mock, fake_fs):
    with open("/etc/cos-alerter.yaml") as f:
        conf = yaml.safe_load(f)
    conf["watch"]["wait_for_first_connection"] = True
    with open("/etc/cos-alerter.yaml", "w") as f:
        yaml.dump(conf, f)
    config.reload()
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    with state:
        monotonic_mock.return_value = 1500
        assert state.is_down() is False  # 6 minutes have passes but we have not started counting.
        state.reset_alert_timeout()
        monotonic_mock.return_value = 1680
        assert state.is_down() is False  # Three more minutes.
        monotonic_mock.return_value = 1830
        assert state.is_down() is True  # 5.5 minutes since reset_alert_timeout() was called.


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_is_down_from_graceful_shutdown(monotonic_mock, fake_fs):
    with open("/etc/cos-alerter.yaml") as f:
        conf = yaml.safe_load(f)
    conf["watch"]["wait_for_first_connection"] = True
    with open("/etc/cos-alerter.yaml", "w") as f:
        yaml.dump(conf, f)
    config.reload()
    fake_fs.create_file(config["clients_file"])
    with config["clients_file"].open("w") as f:
        f.write('{"clientid1": {"alert_time": 500, "notify_time": null}}')
    monotonic_mock.return_value = 1000
    print("Hello Test")
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    with state:
        print(list(AlerterState.clients()))
        print(state.data)
        assert state.is_down() is False
        monotonic_mock.return_value = 2330
        assert state.is_down() is True


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_recently_notified(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    with state:
        state._set_notify_time()
        monotonic_mock.return_value = 2800  # 30 minutes have passed
        assert state._recently_notified() is True
        monotonic_mock.return_value = 5200  # 70 minutes have passed
        assert state._recently_notified() is False


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
@unittest.mock.patch.object(apprise.Apprise, "add")
@unittest.mock.patch.object(apprise.Apprise, "notify")
@unittest.mock.patch.object(EventsAPISession, "trigger")
def test_notify(pd_mock, notify_mock, add_mock, monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    dedup_key = f"{state.clientid}-{state.last_alert_datetime()}"
    with state:
        state.notify()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()

    assert_notifications(
        notify_mock=notify_mock,
        add_mock=add_mock,
        pd_mock=pd_mock,
        title="**Alertmanager is Down!**",
        body=textwrap.dedent("""
            Your Alertmanager instance: clientid1 seems to be down!
            It has not alerted COS-Alerter ever.
            """),
        dedup_key=dedup_key,
    )

    # Make sure if we try again, nothing is sent
    notify_mock.reset_mock()
    pd_mock.reset_mock()

    with state:
        state.notify()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()
    notify_mock.assert_not_called()
    pd_mock.assert_not_called()


@unittest.mock.patch.object(apprise.Apprise, "add")
@unittest.mock.patch.object(apprise.Apprise, "notify")
@unittest.mock.patch.object(EventsAPISession, "trigger")
def test_send_test_notification(pd_mock, notify_mock, add_mock, fake_fs):
    send_test_notification()
    assert_notifications(
        notify_mock=notify_mock,
        add_mock=add_mock,
        pd_mock=pd_mock,
        title="COS-Alerter test email.",
        body="This is a test email automatically generated by COS-alerter.",
        dedup_key="test-dedup-key",
    )


def test_last_alert_datetime(fake_fs):
    with freezegun.freeze_time("2026-05-05T05:00:00+00:00") as frozen_datetime:
        AlerterState.initialize()
        state = AlerterState(clientid="clientid1")

        frozen_datetime.tick(timedelta(seconds=75))
        state.reset_alert_timeout()

        expected = datetime.fromisoformat("2026-05-05T05:01:15+00:00")
        assert state.last_alert_datetime() == expected


def test_can_set_and_get_silence_until(fake_fs):
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    t = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state.silence_until(t)
    assert state.get_silenced_until() == t


def test_silenced_until_persists_between_restarts(fake_fs):
    # set time
    AlerterState.initialize()

    state1 = AlerterState(clientid="clientid1")
    t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state1.silence_until(t1)

    state2 = AlerterState(clientid="another-client")
    t2 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state2.silence_until(t2)

    # save
    AlerterState.dump_and_pause()

    # reload
    AlerterState.initialize()
    state1 = AlerterState(clientid="clientid1")
    state2 = AlerterState(clientid="another-client")

    assert state1.get_silenced_until() == t1
    assert state2.get_silenced_until() == t2


def test_silenced_until_unsilence_persists_between_restarts(fake_fs):
    # set time
    AlerterState.initialize()

    state1 = AlerterState(clientid="clientid1")
    t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    state1.silence_until(t1)
    state1.silence_until(None)

    # save
    AlerterState.dump_and_pause()

    # reload
    AlerterState.initialize()
    state1 = AlerterState(clientid="clientid1")

    assert state1.get_silenced_until() is None


def test_silenced_until_defaults_to_none(fake_fs):
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    assert state.get_silenced_until() is None


def test_is_silenced__none(fake_fs):
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    assert state.is_silenced() is False


@freezegun.freeze_time("2026-04-17T15:33:23.690551+00:00")
def test_is_silenced__1s_past(fake_fs):
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    state.silence_until(datetime.fromisoformat("2026-04-17T15:33:22.690551+00:00"))
    assert state.is_silenced() is False


@freezegun.freeze_time("2026-04-17T15:33:23.690551+00:00")
def test_is_silenced__1s_remaining(fake_fs):
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    state.silence_until(datetime.fromisoformat("2026-04-17T15:33:24.690551+00:00"))
    assert state.is_silenced() is True


@pytest.mark.parametrize(
    "is_silenced,is_down,expected",
    [
        (True, True, False),
        (True, False, False),
        (False, True, True),
        (False, False, False),
    ],
)
def test_should_act(is_silenced, is_down, expected, fake_fs):
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    with unittest.mock.patch.multiple(
        "cos_alerter.alerter.AlerterState",
        is_down=unittest.mock.DEFAULT,
        is_silenced=unittest.mock.DEFAULT,
    ) as mocks:
        mocks["is_down"].return_value = is_down
        mocks["is_silenced"].return_value = is_silenced
        assert state.should_act() is expected


@freezegun.freeze_time("2026-04-17T15:33:23.690551+00:00")
@unittest.mock.patch.object(AlerterState, "resolve_existing_alerts")
@unittest.mock.patch.object(AlerterState, "is_down")
@pytest.mark.parametrize("is_down", [True, False])
def test_unsilence_on_reset_alert_timeout(
    mock_is_down, mock_resolve_existing_alerts, is_down, fake_fs
):
    AlerterState.initialize()
    state = AlerterState(clientid="clientid1")
    state.silence_until(datetime.fromisoformat("2026-05-17T15:33:24.690551+00:00"))
    assert state.is_silenced() is True
    mock_is_down.return_value = is_down
    state.reset_alert_timeout()
    assert state.is_silenced() is False
