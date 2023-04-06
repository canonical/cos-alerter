# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTP server for COS Alerter."""

import logging

from flask import Flask, request

from .alerter import AlerterState

app = Flask(__name__)


@app.route("/alive", methods=["POST"])
def alive():
    """Endpoint for Alertmanager instances to send their heartbeat alerts."""
    # TODO Decide if we should validate the request.
    logging.info("Received alert from Alertmanager.")
    with AlerterState() as state:
        state.reset_alert_timeout()
    return "Success!"


@app.before_request
def log_request():
    """Log every HTTP request."""
    logging.info(
        "Request: %s %s",
        request.method,
        request.url,
    )
