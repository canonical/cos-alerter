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

import waitress

from .alerter import AlerterState, config, send_test_notification
from .server import app

LOG_LEVEL_CHOICES = {
    "CRITICAL": logging.CRITICAL,
    "critical": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "error": logging.ERROR,
    "WARNING": logging.WARNING,
    "warning": logging.WARNING,
    "INFO": logging.INFO,
    "info": logging.INFO,
    "DEBUG": logging.DEBUG,
    "debug": logging.DEBUG,
}


def sigint(_, __):  # pragma: no cover
    """Signal handler to exit cleanly on SIGINT."""
    logging.info("Received SIGINT.")
    logging.debug("Exiting.")
    sys.exit()


def sigusr1(_, __):  # pragma: no cover
    """Signal handler for SIGUSR1 which sends a test notification."""
    logging.info("Received SIGUSR1.")
    send_thread = threading.Thread(target=send_test_notification)
    send_thread.start()


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-level",
        choices=list(LOG_LEVEL_CHOICES),
        help='Logging level. Overrides config value "log_level"',
    )
    return parser.parse_args()


def main(run_for=None):
    """Main method for COS Alerter.

    Args:
        run_for: This argument is for testing purposes. If set, only run for "run_for" seconds.
    """
    args = parse_args()

    if args.log_level:
        log_level = LOG_LEVEL_CHOICES[args.log_level]
    else:
        log_level = LOG_LEVEL_CHOICES[config["log_level"]]
    logfmt = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=log_level, format=logfmt)

    # Initialize the COS Alerter state file
    AlerterState.initialize()

    # Observe signal handlers
    try:
        signal.signal(signal.SIGINT, sigint)  # pragma: no cover
        signal.signal(signal.SIGUSR1, sigusr1)  # pragma: no cover
        logging.debug("Signal handlers set.")
    except ValueError as e:
        # If we are not in the main thread, we can not start the signal handlers.
        # This is okay.
        if not str(e) == "signal only works in main thread of the main interpreter":
            raise  # pragma: no cover

    # Start the web server.
    # Starting in a thread rather than a new process allows waitress to inherit the log level
    # from the daemon. It also facilitates communication over memory rather than files.
    server_thread = threading.Thread(target=waitress.serve, args=(app,))
    server_thread.daemon = True  # Makes this thread exit when the main thread exits.
    logging.info("Starting the web server thread.")
    server_thread.start()

    # Main loop
    state = AlerterState()
    while True:
        with state:
            if run_for and state.up_time() >= run_for:
                return
            logging.debug("Checking Alertmanager status.")
            if state.is_down():
                logging.debug("Alertmanager is down.")
                state.notify()
        time.sleep(1)


if __name__ == "__main__":
    main()  # pragma: no cover
