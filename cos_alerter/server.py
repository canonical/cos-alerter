# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTP server for COS Alerter."""

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
            clients.append(
                {
                    "clientid": clientid,
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
    if len(clientid_list) < 1:
        logger.warning("Request %s has no clientid.", request.url)
        return 'Parameter "clientid" required.', 400
    if len(clientid_list) > 1:
        logger.warning("Request %s specified clientid more than once.", request.url)
        return 'Parameter "clientid" provided more than once.', 400
    clientid = clientid_list[0]
    if clientid not in config["watch"]["clients"]:
        logger.warning("Request %s specified an unknown clientid.")
        return 'Clientid {params["clientid"]} not found. ', 404
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
