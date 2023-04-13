# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main logic for COS Alerter."""

import datetime
import logging
import textwrap
import threading
import time

import apprise
import durationpy
import yaml

logger = logging.getLogger(__name__)


class Config:
    """Representation of the config file."""

    def __getitem__(self, key):
        """Dict style access for config values."""
        return self.data[key]

    def reload(self):
        """Reload config values from the disk."""
        with open("/etc/cos-alerter.yaml", "r") as f:
            self.data = yaml.safe_load(f)
        self.data["watch"]["down_interval"] = durationpy.from_str(
            self.data["watch"]["down_interval"]
        ).total_seconds()
        self.data["notify"]["repeat_interval"] = durationpy.from_str(
            self.data["notify"]["repeat_interval"]
        ).total_seconds()


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

    def _last_alert_datetime(self) -> datetime.datetime:
        """Return the actual time the last alert was received.

        Returns:
            A datetime.datetime object representing the time of the last alert.
        """
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
        last_alert_time = self._last_alert_datetime().isoformat()
        title = "**Alertmanager is Down!**"
        body = textwrap.dedent(
            f"""
            Your Alertmanager instance: {self.clientid} seems to be down!
            It has not alerted COS-Alerter since {last_alert_time} UTC.
            """
        )

        # Sending notifications can be a long operation so handle that in a separate thread.
        # This avoids interfering with the execution of the main loop.
        notify_thread = threading.Thread(
            target=send_notifications, kwargs={"title": title, "body": body}
        )
        notify_thread.start()


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
