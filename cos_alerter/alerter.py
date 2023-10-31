# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main logic for COS Alerter."""

import datetime
import logging
import os
import textwrap
import threading
import time
import typing
from pathlib import Path

import apprise
import durationpy
import yaml

logger = logging.getLogger(__name__)


class Config:
    """Representation of the config file."""

    def __getitem__(self, key):
        """Dict style access for config values."""
        return self.data[key]

    def set_path(self, path: str):
        """Set the config file path."""
        self.path = Path(path)

    def reload(self):
        """Reload config values from the disk."""
        with open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "config-defaults.yaml")
        ) as f:
            self.data = yaml.safe_load(f)
        with open(self.path, "r") as f:
            user_data = yaml.safe_load(f)
        deep_update(self.data, user_data)
        self.data["watch"]["down_interval"] = durationpy.from_str(
            self.data["watch"]["down_interval"]
        ).total_seconds()
        self.data["notify"]["repeat_interval"] = durationpy.from_str(
            self.data["notify"]["repeat_interval"]
        ).total_seconds()


def deep_update(base: dict, new: typing.Optional[dict]):
    """Deep dict update.

    Same as dict.update() except it recurses into dubdicts.
    """
    if new is None:
        return
    for key in base:
        if key in new and isinstance(base[key], dict):
            deep_update(base[key], new[key])
        elif key in new:
            base[key] = new[key]


config = Config()
state = {}


class AlerterState:
    """Class representing the state of COS Alerter.

    This class uses files to store the state. It uses locking to ensure safe access from multiple
    threads.
    """

    def __init__(self, clientid: str):
        self.clientid = (
            clientid  # Needed in addition to `self.data` for logging and notifications.
        )
        self.data = state["clients"][clientid]
        self.start_date = state["start_date"]
        self.start_time = state["start_time"]

    def __enter__(self):
        """Enter method for the context manager.

        Acquires an exclusive lock on the backend file and loads it in to memory.
        """
        logger.debug("Acquiring lock for %s.", self.clientid)
        self.data["lock"].acquire()
        return self

    def __exit__(self, _, __, ___):
        """Exit method for the context manager.

        Dumps the new state to disk then releases the lock.
        """
        logger.debug("Releasing lock for %s.", self.clientid)
        self.data["lock"].release()

    @staticmethod
    def initialize():
        """Initialize the global state object.

        Note: This method does not do any locking so do not call it when there might be other
        threads running.
        """
        logger.info("Initializing COS Alerter.")
        current_date = datetime.datetime.now(datetime.timezone.utc)
        current_time = time.monotonic()
        state["start_date"] = datetime.datetime.timestamp(current_date)
        state["start_time"] = current_time

        # state["clients"] should be of the form:
        # {
        #     <client_id>: {
        #         "lock": <client_lock>,
        #         "alert_time": <alert_time>,
        #         "notify_time": <notify_time>,
        #     },
        #     ...
        # }
        state["clients"] = {}
        for client in config["watch"]["clients"]:
            alert_time = None if config["watch"]["wait_for_first_connection"] else current_time
            state["clients"][client] = {
                "lock": threading.Lock(),
                "alert_time": alert_time,
                "notify_time": None,
            }

    @staticmethod
    def clients():
        """Return a list of clientids."""
        for client in state["clients"]:
            yield client

    def reset_alert_timeout(self):
        """Set the "last alert time" to right now."""
        logger.debug("Resetting alert timeout for %s.", self.clientid)
        self.data["alert_time"] = time.monotonic()

    def _set_notify_time(self):
        """Set the "last notification time" to right now."""
        self.data["notify_time"] = time.monotonic()

    def is_down(self) -> bool:
        """Determine if Alertmanager should be considered down based on the last alert."""
        if self.data["alert_time"] is None:
            return False
        return time.monotonic() - self.data["alert_time"] > config["watch"]["down_interval"]

    def _recently_notified(self) -> bool:
        """Determine if a notification has been previously sent within the repeat interval."""
        return (
            state["clients"][self.clientid]["notify_time"]
            and not time.monotonic() - self.data["notify_time"]
            > config["notify"]["repeat_interval"]
        )

    def last_alert_datetime(self) -> typing.Optional[datetime.datetime]:
        """Return the actual time the last alert was received.

        Returns:
            A datetime.datetime object representing the time of the last alert.
        """
        if self.data["alert_time"] is None or self.data["alert_time"] == self.start_time:
            return None
        actual_alert_timestamp = (self.data["alert_time"] - self.start_time) + self.start_date
        return datetime.datetime.fromtimestamp(actual_alert_timestamp, datetime.timezone.utc)

    def notify(self):
        """Send out notifications of the missing Alertmanager if necessary."""
        # If we have already notified recently, do nothing.
        if self._recently_notified():
            logger.debug("Recently notified. Skipping.")
            return

        logger.info("Sending notifications for %s.", self.clientid)
        self._set_notify_time()
        last_alert_datetime = self.last_alert_datetime()
        last_alert_string = (
            f"since {last_alert_datetime.isoformat()} UTC"
            if last_alert_datetime is not None
            else "ever"
        )
        title = "**Alertmanager is Down!**"
        body = textwrap.dedent(
            f"""
            Your Alertmanager instance: {self.clientid} seems to be down!
            It has not alerted COS-Alerter {last_alert_string}.
            """
        )

        # Sending notifications can be a long operation so handle that in a separate thread.
        # This avoids interfering with the execution of the main loop.
        notify_thread = threading.Thread(
            target=send_notifications, kwargs={"title": title, "body": body}
        )
        notify_thread.start()


def now_datetime():
    """Return the current datetime using the monotonic clock."""
    now_timestamp = (time.monotonic() - state["start_time"]) + state["start_date"]
    return datetime.datetime.fromtimestamp(now_timestamp, datetime.timezone.utc)


def up_time():
    """Return number of seconds that the daemon has been running."""
    return time.monotonic() - state["start_time"]


def send_notifications(title: str, body: str):
    """Send a notification to all receivers."""
    # TODO: Since this is run in its own thread, we have to make sure we properly
    # log failures here.
    sender = apprise.Apprise()
    for source in config["notify"]["destinations"]:
        sender.add(source)
    sender.notify(title=title, body=body)


def send_test_notification():
    """Signal handler which sends a test email to all configured receivers."""
    logger.info("Sending test notifications.")
    send_notifications(
        title="COS-Alerter test email.",
        body="This is a test email automatically generated by COS-alerter.",
    )
