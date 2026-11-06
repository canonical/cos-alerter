#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Daemon process for COS Alerter."""

import argparse
import logging
import signal
import sys
import threading
import time
from typing import List, Optional

import waitress

from .alerter import AlerterState, config, send_test_notification, up_time
from .logging import LEVELS, init_logging
from .server import create_app

logger = logging.getLogger("cos_alerter.daemon")


def sigint(_, __):  # pragma: no cover
    """Signal handler to exit cleanly on SIGINT."""
    logger.info("Received SIGINT.")
    logger.debug("Exiting.")
    sys.exit()


def sigterm(_, __):  # pragma: no cover
    """Signal handler for graceful shutdown on sigterm."""
    logger.info("Shutting down.")
    AlerterState.dump_and_pause()
    sys.exit()


def sigusr1(_, __):  # pragma: no cover
    """Signal handler for SIGUSR1 which sends a test notification."""
    logger.info("Received SIGUSR1.")
    send_thread = threading.Thread(target=send_test_notification)
    send_thread.start()


def parse_args(args: List[str]) -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-level",
        choices=list(LEVELS),
        help='Logging level. Overrides config value "log_level"',
    )
    parser.add_argument(
        "--config",
        required=False,
        default="/etc/cos-alerter.yaml",
        help="Path to config file. Defaults to /etc/cos-alerter.yaml",
    )
    return parser.parse_args(args=args)


def client_loop(clientid):
    """Run the main loop for the specified client."""
    # Main loop
    state = AlerterState(clientid=clientid)
    while True:
        with state:
            logger.debug("Checking Alertmanager status.")
            if state.should_act():
                logger.debug("Alertmanager is down and not silenced.")
                state.notify()
        time.sleep(1)


def main(run_for: Optional[int] = None, argv: List[str] = sys.argv):
    """Main method for COS Alerter.

    Args:
        run_for: This argument is for testing purposes. If set, only run for "run_for" seconds.
        argv: Can be used to override the cli args for testing purposes.
    """
    args = parse_args(argv[1:])

    config.set_path(args.config)
    config.reload()
    init_logging(args)
    AlerterState.initialize()

    # Observe signal handlers
    try:  # pragma: no cover
        signal.signal(signal.SIGINT, sigint)
        signal.signal(signal.SIGTERM, sigterm)
        signal.signal(signal.SIGUSR1, sigusr1)
        logger.debug("Signal handlers set.")
    except ValueError as e:
        # If we are not in the main thread, we can not start the signal handlers.
        # This is okay.
        if not str(e) == "signal only works in main thread of the main interpreter":
            raise  # pragma: no cover

    # Start the web server(s).
    # Starting in a thread rather than a new process allows waitress to inherit the log level
    # from the daemon. It also facilitates communication over memory rather than files.
    # clear_untrusted_proxy_headers is set to suppress a DeprecationWarning.
    # If dashboard_lister_addr exists, serve api and dashboard in their own respective addresses

    dashboard_listen_addr = config["dashboard_listen_addr"]
    web_listen_addr = config["web_listen_addr"]

    if dashboard_listen_addr:
        logger.info(
            "Starting API server on %s, dashboard on %s",
            config["web_listen_addr"],
            dashboard_listen_addr,
        )

        # API server
        api_app = create_app(include_api=True, include_dashboard=False)
        api_server_thread = threading.Thread(
            target=waitress.serve,
            args=(api_app,),
            kwargs={
                "clear_untrusted_proxy_headers": True,
                "listen": web_listen_addr,
            },
        )
        api_server_thread.daemon = True
        api_server_thread.start()

        # Dashboard server
        dashboard_app = create_app(include_api=False, include_dashboard=True)
        dashboard_server_thread = threading.Thread(
            target=waitress.serve,
            args=(dashboard_app,),
            kwargs={
                "clear_untrusted_proxy_headers": True,
                "listen": dashboard_listen_addr,
            },
        )
        dashboard_server_thread.daemon = True
        dashboard_server_thread.start()

    else:
        logger.info("Starting API server and dashboard on %s", config["web_listen_addr"])
        app = create_app(include_api=True, include_dashboard=True)
        server_thread = threading.Thread(
            target=waitress.serve,
            args=(app,),
            kwargs={
                "clear_untrusted_proxy_headers": True,
                "listen": web_listen_addr,
            },
        )
        server_thread.daemon = True
        server_thread.start()

    for clientid in config["watch"]["clients"]:
        client_thread = threading.Thread(target=client_loop, args=(clientid,))
        client_thread.daemon = True  # Makes this thread exit when the main thread exits.
        logger.info("Starting worker thread for client: %s", clientid)
        client_thread.start()

    while True:
        if run_for is not None and up_time() >= run_for:
            return
        time.sleep(1)


if __name__ == "__main__":
    main()  # pragma: no cover
