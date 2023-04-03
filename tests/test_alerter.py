# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import time
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
    current_time = time.monotonic()
    with open("/run/cos-alerter-data", "w") as f:
        json.dump(
            {
                "start_date": 1680125340.127957,
                "start_time": current_time,
                "alert_time": current_time,
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
def test_is_down_with_set_alert_time(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    state = AlerterState()
    state.initialize()
    with state:
        monotonic_mock.return_value = 2000
        state.set_alert_time()
        monotonic_mock.return_value = 2180  # Three minutes have passed
        assert state.is_down() is False
        monotonic_mock.return_value = 2330  # Five and a half minutes have passed
        assert state.is_down() is True


@freezegun.freeze_time("2023-01-01")
@unittest.mock.patch("time.monotonic")
def test_notify(monotonic_mock, fake_fs):
    monotonic_mock.return_value = 1000
    state = AlerterState()
    state.initialize()
    with state:
        monotonic_mock.return_value = 2000
        state.set_alert_time()
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


# TODO figure out how to properly test notify() and send_notifications()
