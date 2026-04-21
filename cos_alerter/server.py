# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""HTTP server for COS Alerter."""

import datetime
import hashlib
import hmac
import logging
from typing import Optional

import timeago
from flask import Flask, redirect, render_template, request
from prometheus_flask_exporter import PrometheusMetrics

from .alerter import AlerterState, config, now_datetime

logger = logging.getLogger(__name__)


def create_app(include_api: bool = True, include_dashboard: bool = True) -> Flask:
    """Create Flask app with specified endpoints.

    Args:
        include_api: Whether to include the /alive API endpoint
        include_dashboard: Whether to include the / dashboard endpoint

    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    metrics = PrometheusMetrics(app)  # noqa: F841

    if include_dashboard:

        @app.route("/", methods=["GET"])
        def dashboard_route():
            return dashboard()

        @app.route("/clients/<client_id>", methods=["GET"])
        def user_details(client_id):
            return client_details(client_id)

        @app.route("/silence/<client_id>", methods=["POST"])
        def silence(client_id):
            return silence_client(client_id)

    if include_api:

        @app.route("/alive", methods=["POST"])
        def alive_route():
            return alive()

    @app.before_request
    def log_request_wrapper():
        return log_request()

    return app


def get_client_details(clientid):
    """Return a dict with various details about a client."""
    now = now_datetime()
    with AlerterState(clientid) as state:
        last_alert = state.last_alert_datetime()
        alert_time = timeago.format(last_alert, now) if last_alert is not None else "never"
        silenced_until = state.get_silenced_until()
        remaining_silence = (
            timeago.format(silenced_until, now) if silenced_until is not None else "never"
        )
        status = "up" if not state.is_down() else "down"
        if last_alert is None:
            status = "unknown"
        client_name = config["watch"]["clients"][clientid].get("name", "")
        return {
            "client_id": clientid,
            "client_name": client_name,
            "status": status,
            "alert_time": alert_time,
            "is_silenced": state.is_silenced(),
            "silenced_until": state.get_silenced_until_iso_str(),
            "remaining_silence": remaining_silence,
        }


def dashboard():
    """Endpoint for the COS Alerter dashboard."""
    clients = [get_client_details(clientid) for clientid in AlerterState.clients()]
    return render_template("dashboard.html", clients=clients)


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
    if not _is_key_correct(clientid, key):
        logger.warning("Request %s provided an incorrect key.", request.url)
        return "Incorrect key for the specified clientid.", 401
    logger.info("Received alert from Alertmanager clientid: %s.", clientid)
    with AlerterState(clientid) as state:
        state.reset_alert_timeout()
    return "Success!"


def _is_key_correct(clientid: str, key: Optional[str]) -> bool:
    """Check the provided client key.

    It assumes that the clientid exists.
    """
    if key is None:
        return False
    stored_hash = config["watch"]["clients"][clientid]["key"]
    client_hash = hashlib.sha512(key.encode()).hexdigest()
    return hmac.compare_digest(stored_hash, client_hash)


def client_details(client_id):
    """Return a page with client-level features."""
    if client_id not in config["watch"]["clients"]:
        return f"Clientid {client_id} not found.", 404
    return render_template("client-details.html", client=get_client_details(client_id))


def silence_client(client_id):
    """Endpoint for silencing a client."""
    if client_id not in config["watch"]["clients"]:
        return f"Clientid {client_id} not found.", 404

    key = request.form.get("client-key")
    if not _is_key_correct(client_id, key):
        return "Invalid credentials", 401

    silence_period_h = request.form.get("silence-duration-h", type=int)
    if silence_period_h is None:
        return "Invalid silence period.", 400

    now = datetime.datetime.now(datetime.timezone.utc)
    silence_until = now + datetime.timedelta(hours=silence_period_h)
    with AlerterState(client_id) as state:
        state.silence_until(silence_until)
    return redirect("/")


def log_request():
    """Log every HTTP request."""
    logger.info(
        "Request: %s %s",
        request.method,
        request.url,
    )
