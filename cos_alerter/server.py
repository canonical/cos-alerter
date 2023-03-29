# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTP server for COS Alerter."""

from flask import Flask

from .alerter import AlerterState

app = Flask(__name__)


@app.route("/alive", methods=["POST"])
def alive():
    """Endpoint for Alertmanager instances to send their heartbeat alerts."""
    # TODO Decide if we should validate the request.
    with AlerterState() as state:
        state.reset_alert_timeout()
    return "Success!"
