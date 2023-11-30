# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import copy

import pytest
import yaml
from helpers import CONFIG
from werkzeug.datastructures import MultiDict

from cos_alerter.alerter import AlerterState, config
from cos_alerter.server import app

PARAMS = {"clientid": "clientid1", "key": "clientkey1"}


@pytest.fixture
def flask_client():
    return app.test_client()


@pytest.fixture
def state_init():
    AlerterState.initialize()


def test_dashboard_succeeds(flask_client, fake_fs, state_init):
    assert flask_client.get("/").status_code == 200


def test_alive_succeeds(flask_client, fake_fs, state_init):
    response = flask_client.post("/alive", query_string=PARAMS)
    assert response.status_code == 200
    assert len(response.data) > 0


def test_alive_other_methods_fail(flask_client, fake_fs, state_init):
    assert flask_client.get("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.head("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.put("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.delete("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.patch("/alive", query_string=PARAMS).status_code == 405


def test_alive_updates_time(flask_client, fake_fs, state_init):
    flask_client.post("/alive", query_string=PARAMS)
    state = AlerterState(clientid="clientid1")
    with state:
        assert state.data["alert_time"] > state.start_time


def test_metrics_succeeds(flask_client, fake_fs, state_init):
    assert flask_client.get("/metrics").status_code == 200


def test_no_clientid(flask_client, fake_fs, state_init):
    response = flask_client.post("/alive")
    assert response.status_code == 400
    assert len(response.data) > 0


def test_wrong_clientid(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive",
        query_string={"clientid": "clientid2", "key": "clientkey1"},
    )
    assert response.status_code == 404


def test_duplicate_clientid(flask_client, fake_fs, state_init):
    conf = copy.deepcopy(CONFIG)
    conf["watch"]["clients"]["clientid2"] = {
        "key": "0415b0cad09712bd1ed094bc06ed421231d0603465e9841c959e9f9dcf735c9ce704df7a0c849a4e0db405c916f679a0e6c3f63f9e26191dda8069e1b44a3bc8",
        "name": "Client 2",
    }
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(yaml.dump(conf))
    config.reload()
    params = MultiDict(
        [
            ("clientid", "clientid1"),
            ("key", "clientkey1"),
            ("clientid", "clientid2"),
            ("key", "clientkey2"),
        ]
    )
    response = flask_client.post("/alive", query_string=params)
    assert response.status_code == 400
    assert len(response.data) > 0


def test_invalid_key(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive",
        query_string={"clientid": "clientid1", "key": "incorrect-key"},
    )
    assert response.status_code == 401
    assert len(response.data) > 0


def test_missing_key(flask_client, fake_fs, state_init):
    response = flask_client.post("/alive", query_string={"clientid": "clientid1"})
    assert response.status_code == 400
    assert len(response.data) > 0


def test_multiple_key_values(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive",
        query_string={"clientid": "clientid1", "key": ["key1", "key2"]},
    )
    assert response.status_code == 400
    assert len(response.data) > 0
