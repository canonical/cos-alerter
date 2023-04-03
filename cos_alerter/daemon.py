#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Daemon process for COS Alerter."""

import signal
import subprocess
import sys
import time

from .alerter import AlerterState, send_test_notification


def sigint(_, __):
    """Signal handler to exit cleanly on SIGINT."""
    sys.exit()


def sigusr1(_, __):
    """Signal handler for SIGUSR1 which sends a test notification."""
    send_test_notification()


def main():
    """Main method for COS Alerter."""
    # Initialize the COS Alerter state file
    AlerterState.initialize()

    # Observe signal handlers
    signal.signal(signal.SIGINT, sigint)
    signal.signal(signal.SIGUSR1, sigusr1)

    # Start the web server
    subprocess.Popen(["waitress-serve", "cos_alerter.server:app"])

    # Main loop
    state = AlerterState()
    while True:
        with state:
            if state.is_down():
                state.notify()
        time.sleep(1)


if __name__ == "__main__":
    main()
