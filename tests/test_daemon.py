# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import subprocess
import threading
import time
import unittest.mock

import apprise
import pytest
import yaml

from cos_alerter.alerter import AlerterState, config
from cos_alerter.daemon import client_loop, main

DESTINATIONS = [
    "mailtos://user:pass@domain/?to=example-0@example.com,example-1@example.com",
    "slack://xoxb-1234-1234-4ddbc191d40ee098cbaae6f3523ada2d/#general",
]

WATCH = {
    "down_interval": "4s",
    "wait_for_first_connection": False,
    "clients": {
        "clientid1": {
            "key": "822295b207a0b73dd4690b60a03c55599346d44aef3da4cf28c3296eadb98b2647ae18863cc3ae8ae5574191b60360858982fd8a8d176c0edf646ce6eee24ef9",
            "name": "Instance Name 1",
        },
    },
}

NOTIFY = {
    "destinations": DESTINATIONS,
    "repeat_interval": "4s",
}


@pytest.fixture
def mock_fs(fake_fs):
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(
            yaml.dump(
                {
                    "watch": WATCH,
                    "notify": NOTIFY,
                    "log_level": "info",
                }
            )
        )
    config.set_path("/etc/cos-alerter.yaml")
    config.reload()
    return fake_fs


@pytest.fixture
def mock_fs_dashboard_addr(fake_fs):
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(
            yaml.dump(
                {
                    "watch": WATCH,
                    "notify": NOTIFY,
                    "log_level": "info",
                    "dashboard_listen_addr": "127.0.0.1:8081",
                }
            )
        )
    config.set_path("/etc/cos-alerter.yaml")
    config.reload()
    return fake_fs


@pytest.mark.slow
@unittest.mock.patch.object(apprise.Apprise, "add")
@unittest.mock.patch.object(apprise.Apprise, "notify")
def test_main(notify_mock, add_mock, mock_fs):
    main_thread = threading.Thread(target=main, kwargs={"run_for": 13, "argv": ["cos-alerter"]})
    try:
        main_thread.start()
        time.sleep(2)  # Should not be considered down yet.
        notify_mock.assert_not_called()
        subprocess.call(
            [
                "curl",
                "-X",
                "POST",
                "http://localhost:8080/alive?clientid=clientid1&key=clientkey1",
            ]
        )
        time.sleep(3)  # Would be considered down but we just sent an alive call.
        notify_mock.assert_not_called()
        time.sleep(3)  # It has been > 4 seconds since we last alerted so it should be down.
        notify_mock.assert_called()
        time.sleep(1)  # Should still have only been called once.
        notify_mock.assert_called_once()
        time.sleep(4)  # Now should be called a second time.
        assert notify_mock.call_count == 2
    finally:
        main_thread.join()


# TODO We need a test here for multiple clients. The problem is that the waitress thread does not
# close when the previous test ends and so the socket is held open.


def test_log_level_arg(mock_fs):
    main(run_for=0, argv=["cos-alerter", "--log-level", "DEBUG"])
    assert logging.getLogger("cos_alerter").getEffectiveLevel() == logging.DEBUG


@unittest.mock.patch.object(AlerterState, "notify")
@unittest.mock.patch.object(AlerterState, "should_act", return_value=True)
@unittest.mock.patch("cos_alerter.daemon.time.sleep", side_effect=StopIteration)
def test_client_loop_when_should_act(sleep_mock, should_act_mock, notify_mock, mock_fs):
    AlerterState.initialize()  # We need to initialize the state before calling client_loop
    with pytest.raises(StopIteration):
        client_loop("clientid1")
    should_act_mock.assert_called_once()
    notify_mock.assert_called_once()


@unittest.mock.patch("cos_alerter.daemon.create_app")
@unittest.mock.patch("cos_alerter.daemon.waitress.serve")
def test_main_with_dashboard_addr(waitress_serve_mock, create_app_mock, mock_fs_dashboard_addr):
    main(run_for=0, argv=["cos-alerter"])
    assert create_app_mock.call_count == 2  # Called once for API and once for dashboard
