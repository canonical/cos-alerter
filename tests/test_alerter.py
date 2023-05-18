# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import textwrap
import threading
import unittest.mock

import apprise
import freezegun
import yaml
from helpers import DESTINATIONS

from cos_alerter.alerter import AlerterState, config, send_test_notification, up_time


def assert_notifications(notify_mock, add_mock, title, body):
    add_mock.assert_has_calls([unittest.mock.call(x) for x in DESTINATIONS])
    notify_mock.assert_called_with(title=title, body=body)


def test_config_gets_item(fake_fs):
    assert config["watch"]["down_interval"] == 300


def test_config_default_empty_file(fake_fs):
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write("")
    config.reload()
    assert config["watch"]["down_interval"] == 300


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
    state = AlerterState(clientid="client0")
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
    state = AlerterState(clientid="client0")
    with state:
        monotonic_mock.return_value = 1180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 1330  # Five and a half minutes have passed
        assert state.is_down() is True


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_is_down_with_reset_alert_timeout(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="client0")
    with state:
        monotonic_mock.return_value = 2000
        state.reset_alert_timeout()
        monotonic_mock.return_value = 2180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 2330  # Five and a half minutes have passed
        assert state.is_down() is True


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
    state = AlerterState(clientid="client0")
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
def test_is_down(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="client0")
    with state:
        monotonic_mock.return_value = 2000
        state.reset_alert_timeout()
        monotonic_mock.return_value = 2180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 2330  # Five and a half minutes have passed
        assert state.is_down() is True


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_recently_notified(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="client0")
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
def test_notify(notify_mock, add_mock, monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    AlerterState.initialize()
    state = AlerterState(clientid="client0")

    with state:
        state.notify()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()
    assert_notifications(
        notify_mock,
        add_mock,
        title="**Alertmanager is Down!**",
        body=textwrap.dedent(
            """
            Your Alertmanager instance: client0 seems to be down!
            It has not alerted COS-Alerter since Never.
            """
        ),
    )

    # Make sure if we try again, nothing is sent
    notify_mock.reset_mock()

    with state:
        state.notify()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()
    notify_mock.assert_not_called()


@unittest.mock.patch.object(apprise.Apprise, "add")
@unittest.mock.patch.object(apprise.Apprise, "notify")
def test_send_test_notification(notify_mock, add_mock, fake_fs):
    send_test_notification()
    assert_notifications(
        notify_mock,
        add_mock,
        title="COS-Alerter test email.",
        body="This is a test email automatically generated by COS-alerter.",
    )
