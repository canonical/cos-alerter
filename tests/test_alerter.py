# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import textwrap
import threading
import unittest.mock

import apprise
import freezegun
import pytest
import yaml

from cos_alerter.alerter import AlerterState, config, send_test_notification

DESTINATIONS = [
    "mailtos://user:pass@domain/?to=example-0@example.com,example-1@example.com",
    "slack://xoxb-1234-1234-4ddbc191d40ee098cbaae6f3523ada2d/#general",
]


@pytest.fixture
def fake_fs(fs):
    fs.create_file("/etc/cos-alerter.yaml")
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(
            yaml.dump(
                {
                    "watch": {
                        "data_file": "/run/cos-alerter-data",
                        "down_interval": "5m",
                    },
                    "notify": {
                        "destinations": DESTINATIONS,
                        "repeat_interval": "1h",
                    },
                }
            )
        )

    fs.create_file("/run/cos-alerter-data")
    with open("/run/cos-alerter-data", "w") as f:
        json.dump(
            {
                "start_date": 1672531200.0,
                "start_time": 1000,
                "alert_time": 1000,
                "notify_time": None,
            },
            f,
        )

    return fs


def assert_notifications(notify_mock, add_mock, title, body):
    add_mock.assert_has_calls([unittest.mock.call(x) for x in DESTINATIONS])
    notify_mock.assert_called_with(title=title, body=body)


def test_config_gets_item(fake_fs):
    assert config["watch"]["data_file"] == "/run/cos-alerter-data"


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_initialize(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    state = AlerterState()
    state.initialize()
    with state:
        assert state.data["start_date"] == 1672531200.0
        assert state.data["start_time"] == 1000
        assert state.data["alert_time"] == 1000
        assert state.data["notify_time"] is None


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_up_time(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 2000
    state = AlerterState()
    with state:
        assert state.up_time() == 1000


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_is_down_from_initialize(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    state = AlerterState()
    state.initialize()
    with state:
        monotonic_mock.return_value = 1180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 1330  # Five and a half minutes have passed
        assert state.is_down() is True


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_is_down_with_reset_alert_timeout(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    state = AlerterState()
    state.initialize()
    with state:
        monotonic_mock.return_value = 2000
        state.reset_alert_timeout()
        monotonic_mock.return_value = 2180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 2330  # Five and a half minutes have passed
        assert state.is_down() is True


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_is_down(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    state = AlerterState()
    state.initialize()
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
    state = AlerterState()
    state.initialize()
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
    state = AlerterState()

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
            Your Alertmanager instance seems to be down!
            It has not alerted COS-Alerter since 2023-01-01T00:00:00+00:00 UTC.
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
