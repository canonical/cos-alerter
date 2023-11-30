# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTP server for COS Alerter."""

import hashlib
import logging

import timeago
from flask import Flask, render_template, request
from prometheus_flask_exporter import PrometheusMetrics

from .alerter import AlerterState, config, now_datetime

app = Flask(__name__)
metrics = PrometheusMetrics(app)
logger = logging.getLogger(__name__)


@app.route("/", methods=["GET"])
def dashboard():
    """Endpoint for the COS Alerter dashboard."""
    clients = []
    now = now_datetime()
    for clientid in AlerterState.clients():
        with AlerterState(clientid) as state:
            last_alert = state.last_alert_datetime()
            alert_time = timeago.format(last_alert, now) if last_alert is not None else "never"
            status = "up" if not state.is_down() else "down"
            if last_alert is None:
                status = "unknown"
            client_name = config["watch"]["clients"][clientid].get("name", "")
            clients.append(
                {
                    "client_name": client_name,
                    "status": status,
                    "alert_time": alert_time,
                }
            )
    return render_template("dashboard.html", clients=clients)


@app.route("/alive", methods=["POST"])
def alive():
    """Endpoint for Alertmanager instances to send their heartbeat alerts."""
    # TODO Decide if we should validate the request.
    params = request.args
    clientid_list = params.getlist("clientid")  # params is a werkzeug.datastructures.MultiDict
    key_list = params.getlist("key")

    if len(clientid_list) < 1 or len(key_list) < 1:
        logger.warning("Request %s is missing clientid or key.", request.url)
        return 'Parameters "clientid" and "key" are required.', 400
    if len(clientid_list) > 1 or len(key_list) > 1:
        logger.warning("Request %s specified clientid or key more than once.", request.url)
        return 'Parameters "clientid" and "key" should be provided exactly once.', 400
    clientid = clientid_list[0]
    key = key_list[0]

    # Find the client with the specified clientid
    client_info = config["watch"]["clients"].get(clientid)
    if not client_info:
        logger.warning("Request %s specified an unknown clientid.", request.url)
        return 'Clientid {params["clientid"]} not found. ', 404

    # Hash the key and compare with the stored hashed key
    hashed_key = hashlib.sha512(key.encode()).hexdigest()
    if hashed_key != client_info.get("key", ""):
        logger.warning("Request %s provided an incorrect key.", request.url)
        return "Incorrect key for the specified clientid.", 401
    logger.info("Received alert from Alertmanager clientid: %s.", clientid)
    with AlerterState(clientid) as state:
        state.reset_alert_timeout()
    return "Success!"


@app.before_request
def log_request():
    """Log every HTTP request."""
    logger.info(
        "Request: %s %s",
        request.method,
        request.url,
    )
