# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import copy
from pathlib import Path

import pytest
import yaml
from werkzeug.datastructures import MultiDict

from cos_alerter.alerter import AlerterState, config
from cos_alerter.server import app

PARAMS = {"clientid": "client0"}
CONFIG = {
    "watch": {
        "down_interval": "5m",
        "wait_for_first_connection": True,
        "clients": ["client0"],
    },
    "notify": {
        "destinations": [],
        "repeat_interval": "1h",
    },
    "log_level": "info",
}


@pytest.fixture
def flask_client():
    return app.test_client()


@pytest.fixture
def fake_fs(fs):
    fs.create_file("/etc/cos-alerter.yaml")
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(yaml.dump(CONFIG))
    config.set_path(Path("/etc/cos-alerter.yaml"))
    config.reload()
    return fs


@pytest.fixture
def state_init():
    AlerterState.initialize()


def test_alive_succeeds(flask_client, fake_fs, state_init):
    assert flask_client.post("/alive", query_string=PARAMS).status_code == 200


def test_alive_other_methods_fail(flask_client, fake_fs, state_init):
    assert flask_client.get("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.head("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.put("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.delete("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.patch("/alive", query_string=PARAMS).status_code == 405


def test_alive_updates_time(flask_client, fake_fs, state_init):
    flask_client.post("/alive", query_string=PARAMS)
    state = AlerterState(clientid="client0")
    with state:
        assert state.data["alert_time"] > state.start_time


def test_no_clientid(flask_client, fake_fs, state_init):
    assert flask_client.post("/alive").status_code == 400


def test_wrong_clientid(flask_client, fake_fs, state_init):
    assert flask_client.post("/alive", query_string={"clientid": "client1"}).status_code == 404


def test_duplicate_clientid(flask_client, fake_fs, state_init):
    conf = copy.deepcopy(CONFIG)
    conf["watch"]["clients"].append("client1")
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(yaml.dump(conf))
    config.reload()
    params = MultiDict(
        [
            ("clientid", "client0"),
            ("clientid", "client1"),
        ]
    )
    assert flask_client.post("/alive", query_string=params).status_code == 400
