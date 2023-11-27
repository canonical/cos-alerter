# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import copy

import pytest
import yaml
from helpers import CONFIG
from werkzeug.datastructures import MultiDict

from cos_alerter.alerter import AlerterState, config
from cos_alerter.server import app, get_name_for_uuid

PARAMS = {"clientid": "123e4567-e89b-12d3-a456-426614174001", "key": "jk3h4g5j34h0"}


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
    assert response.data.decode("utf-8") == "Success!"


def test_alive_other_methods_fail(flask_client, fake_fs, state_init):
    assert flask_client.get("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.head("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.put("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.delete("/alive", query_string=PARAMS).status_code == 405
    assert flask_client.patch("/alive", query_string=PARAMS).status_code == 405


def test_alive_updates_time(flask_client, fake_fs, state_init):
    flask_client.post("/alive", query_string=PARAMS)
    state = AlerterState(clientid="123e4567-e89b-12d3-a456-426614174001")
    with state:
        assert state.data["alert_time"] > state.start_time


def test_metrics_succeeds(flask_client, fake_fs, state_init):
    assert flask_client.get("/metrics").status_code == 200


def test_no_clientid(flask_client, fake_fs, state_init):
    response = flask_client.post("/alive")
    assert response.status_code == 400
    assert 'Parameters "clientid" and "key" are required.' in response.get_data(as_text=True)


def test_wrong_clientid(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive",
        query_string={"clientid": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", "key": "jk3h4g5j34h0"},
    )
    assert response.status_code == 404


def test_duplicate_clientid(flask_client, fake_fs, state_init):
    conf = copy.deepcopy(CONFIG)
    conf["watch"]["clients"].append("client1")
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(yaml.dump(conf))
    config.reload()
    params = MultiDict(
        [
            ("clientid", "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"),
            ("key", "jk3o4g5j34h0"),
            ("clientid", "123e4567-e89b-12d3-a456-426614174001"),
            ("key", "jk3h4g5j34h0"),
        ]
    )
    response = flask_client.post("/alive", query_string=params)
    assert response.status_code == 400
    assert 'Parameters "clientid" and "key" should be provided exactly once.' in response.get_data(
        as_text=True
    )


def test_invalid_uuid_format(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive", query_string={"clientid": "invalid-uuid", "key": "jk3h4g5j34h0"}
    )
    assert response.status_code == 400
    assert "not a valid UUID" in response.get_data(as_text=True)


def test_invalid_key(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive",
        query_string={"clientid": "123e4567-e89b-12d3-a456-426614174001", "key": "incorrect-key"},
    )
    assert response.status_code == 401
    assert "Incorrect key for the specified clientid" in response.get_data(as_text=True)


def test_missing_key(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive", query_string={"clientid": "123e4567-e89b-12d3-a456-426614174001"}
    )
    assert response.status_code == 400
    assert 'Parameters "clientid" and "key" are required.' in response.get_data(as_text=True)


def test_multiple_key_values(flask_client, fake_fs, state_init):
    response = flask_client.post(
        "/alive",
        query_string={"clientid": "123e4567-e89b-12d3-a456-426614174001", "key": ["key1", "key2"]},
    )
    assert response.status_code == 400
    assert 'Parameters "clientid" and "key" should be provided exactly once.' in response.get_data(
        as_text=True
    )


def test_get_name_for_uuid_found():
    clients = [
        {"id": "clientuuid1", "key": "test_key1", "name": "test_name_1"},
        {"id": "clientuuid2", "key": "test_key2", "name": "test_name_2"},
    ]

    target_uuid = "clientuuid1"
    result = get_name_for_uuid(target_uuid, clients)

    assert result == "test_name_1"


def test_get_name_for_uuid_not_found():
    clients = [
        {"id": "clientuuid1", "key": "test_key1", "name": "test_name_1"},
        {"id": "clientuuid2", "key": "test_key2", "name": "test_name_2"},
    ]

    target_uuid = "nonexistent_uuid"
    result = get_name_for_uuid(target_uuid, clients)

    assert result is None
