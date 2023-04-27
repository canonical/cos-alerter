# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import subprocess
import threading
import time
import unittest.mock
from pathlib import Path

import apprise
import pytest
import yaml

from cos_alerter.alerter import config
from cos_alerter.daemon import main

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
                        "down_interval": "4s",
                        "wait_for_first_connection": False,
                        "clients": ["client0"],
                    },
                    "notify": {
                        "destinations": DESTINATIONS,
                        "repeat_interval": "4s",
                    },
                    "log_level": "info",
                }
            )
        )
    config.set_path(Path("/etc/cos-alerter.yaml"))
    config.reload()
    return fs


@pytest.mark.slow
@unittest.mock.patch.object(apprise.Apprise, "add")
@unittest.mock.patch.object(apprise.Apprise, "notify")
def test_main(notify_mock, add_mock, fake_fs):
    main_thread = threading.Thread(target=main, kwargs={"run_for": 13, "argv": ["cos-alerter"]})
    try:
        main_thread.start()
        time.sleep(2)  # Should not be considered down yet.
        notify_mock.assert_not_called()
        subprocess.call(["curl", "-X", "POST", "http://localhost:8080/alive?clientid=client0"])
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


def test_log_level_arg(fake_fs):
    main(run_for=0, argv=["cos-alerter", "--log-level", "DEBUG"])
    assert logging.getLogger("cos_alerter").getEffectiveLevel() == logging.DEBUG
