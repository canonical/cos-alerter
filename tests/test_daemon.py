# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import subprocess
import threading
import time
import unittest.mock

import apprise
import pytest
import yaml

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
                        "data_file": "/run/cos-alerter-data",
                        "down_interval": "4s",
                    },
                    "notify": {
                        "destinations": DESTINATIONS,
                        "repeat_interval": "4s",
                    },
                }
            )
        )
    fs.create_file("/run/cos-alerter-data")
    return fs


@pytest.mark.slow
@unittest.mock.patch.object(apprise.Apprise, "add")
@unittest.mock.patch.object(apprise.Apprise, "notify")
def test_main(notify_mock, add_mock, fake_fs):
    main_thread = threading.Thread(target=main, kwargs={"run_for": 13})
    try:
        main_thread.start()
        time.sleep(2)  # Should not be considered down yet.
        notify_mock.assert_not_called()
        subprocess.call(["curl", "-X", "POST", "http://localhost:8080/alive"])
        time.sleep(2)  # Would be considered down but we just sent an alive call.
        notify_mock.assert_not_called()
        time.sleep(3)  # It has been > 4 seconds since we last alerted so it should be down.
        notify_mock.assert_called()
        time.sleep(1)  # Should still have only been called once.
        notify_mock.assert_called_once()
        time.sleep(4)  # Now should be called a second time.
        assert notify_mock.call_count == 2
    finally:
        main_thread.join()
