# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import textwrap
import threading
import unittest.mock

import freezegun
import pytest
import yaml

from cos_alerter.alerter import AlerterState, config


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
@unittest.mock.patch("cos_alerter.alerter.send_notifications")
def test_notify(send_mock, monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    state = AlerterState()

    with state:
        state.notify()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()
    send_mock.assert_called_with(
        title="**Alertmanager is Down!**",
        body=textwrap.dedent(
            """
            Your Alertmanager instance seems to be down!
            It has not alerted COS-Alerter since 2023-01-01T00:00:00+00:00 UTC.
            """
        ),
    )

    # Make sure if we try again, nothing is sent
    send_mock.reset_mock()

    with state:
        state.notify()
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join()
    send_mock.assert_not_called()
