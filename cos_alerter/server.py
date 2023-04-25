# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTP server for COS Alerter."""

import logging

from flask import Flask, request
from prometheus_flask_exporter import PrometheusMetrics

from .alerter import AlerterState, config

app = Flask(__name__)
metrics = PrometheusMetrics(app)
logger = logging.getLogger(__name__)


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
