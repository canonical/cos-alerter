#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Daemon process for COS Alerter."""

import signal
import subprocess
import sys
import time

from .alerter import AlerterState, send_test_notification


def sigint(_, __):  # pragma: no cover
    """Signal handler to exit cleanly on SIGINT."""
    sys.exit()


def sigusr1(_, __):  # pragma: no cover
    """Signal handler for SIGUSR1 which sends a test notification."""
    send_test_notification()


def main(run_for=None):
    """Main method for COS Alerter.

    Args:
        run_for: This argument is for testing purposes. If set, only run for "run_for" seconds.
    """
    # Initialize the COS Alerter state file
    AlerterState.initialize()

    # Observe signal handlers
    try:
        signal.signal(signal.SIGINT, sigint)  # pragma: no cover
        signal.signal(signal.SIGUSR1, sigusr1)  # pragma: no cover
    except ValueError as e:
        # If we are not in the main thread, we can not start the signal handlers.
        # This is okay.
        if not str(e) == "signal only works in main thread of the main interpreter":
            raise  # pragma: no cover

    # Start the web server
    subprocess.Popen(["waitress-serve", "cos_alerter.server:app"])

    # Main loop
    state = AlerterState()
    while True:
        with state:
            if run_for and state.up_time() >= run_for:
                return
            if state.is_down():
                state.notify()
        time.sleep(1)


if __name__ == "__main__":
    main()  # pragma: no cover
