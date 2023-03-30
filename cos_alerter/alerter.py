# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Main logic for COS Alerter."""

import datetime
import fcntl
import json
import textwrap
import threading
import time

import apprise
import durationpy
import yaml


class Config:
    """Representation of the config file."""

    def __getitem__(self, key):
        """Dict style acccess for config values."""
        with open("/etc/cos-alerter.yaml", "rb") as f:
            return yaml.safe_load(f)[key]


config = Config()


class AlerterState:
    """Class representing the state of COS Alerter.

    This class uses files to store the state. It uses locking to ensure safe access from multiple
    threads.
    """

    def __enter__(self):
        """Enter method for the context manager.

        Acquires an exclusive lock on the backend file and loads it in to memory.
        """
        self.fh = open(config["watch"]["data_file"], "r+")
        fcntl.lockf(self.fh, fcntl.LOCK_EX)
        self.data = json.load(self.fh)
        return self

    def __exit__(self, _, __, ___):
        """Exit method for the context manager.

        Dumps the new state to disk then releases the lock.
        """
        self.fh.seek(0)
        json.dump(self.data, self.fh)
        self.fh.truncate()
        fcntl.lockf(self.fh, fcntl.LOCK_UN)
        self.fh.close()

    @staticmethod
    def initialize():
        """Initialize the backend data file.

        This method sets all the initial values.

        Note: This method does not do any locking so do not call it when there might be other
        threads running.
        """
        current_date = datetime.datetime.now(datetime.timezone.utc)
        current_time = time.monotonic()
        data = {
            # The actual date and time that COS Alerter was started.
            "start_date": datetime.datetime.timestamp(current_date),
            # The time according to the monotonic clock that COS Alerter was started.
            "start_time": current_time,
            # The last time we received an alert from Alertmanager.
            # This is set to current time instead of None so that the logic a bit more simple
            # when checking if Alertmanager is down.
            "alert_time": current_time,
            # The last time we sent out notifications.
            "notify_time": None,
        }

        with open(config["watch"]["data_file"], "w") as f:
            json.dump(data, f)

    def reset_alert_timeout(self):
        """Set the "last alert time" to right now."""
        self.data["alert_time"] = time.monotonic()

    def _set_notify_time(self):
        """Set the "last notification time" to right now."""
        self.data["notify_time"] = time.monotonic()

    def is_down(self) -> bool:
        """Determine if Alertmanager should be considered down based on the last alert."""
        down_interval = durationpy.from_str(config["watch"]["down_interval"]).total_seconds()
        return time.monotonic() - self.data["alert_time"] > down_interval

    def _recently_notified(self) -> bool:
        """Determine if a notification has been previously sent within the repeat interval."""
        repeat_interval = durationpy.from_str(config["notify"]["repeat_interval"]).total_seconds()
        return (
            self.data["notify_time"]
            and not time.monotonic() - self.data["notify_time"] > repeat_interval
        )

    def _last_alert_datetime(self) -> datetime.datetime:
        """Return the actual time the last alert was received.

        Returns:
            A datetime.datetime object representing the time of the last alert.
        """
        actual_alert_timestamp = (self.data["alert_time"] - self.data["start_time"]) + self.data[
            "start_date"
        ]
        return datetime.datetime.fromtimestamp(actual_alert_timestamp, datetime.timezone.utc)

    def notify(self):
        """Send out notifications of the missing Alertmanager if necessary."""
        # If we have already notified recently, do nothing.
        if self._recently_notified():
            return

        self._set_notify_time()
        last_alert_time = self._last_alert_datetime().isoformat()
        title = "**Alertmanager is Down!**"
        body = textwrap.dedent(
            f"""
            Your Alertmanager instance seems to be down!
            It has not alerted COS-Alerter since {last_alert_time} UTC.
            """
        )

        # Sending notifications can be a long operation so handle that in a separate thread.
        # This avoids interfering with the execution of the main loop.
        notify_thread = threading.Thread(
            target=send_notifications, kwargs={"title": title, "body": body}
        )
        notify_thread.start()


def send_notifications(title, body):
    """Send a notification to all receivers."""
    # TODO: Since this is run in its own thread, we have to make sure we properly
    # log failures here.
    sender = apprise.Apprise()
    for source in config["notify"]["destinations"]:
        sender.add(source)
    sender.notify(title=title, body=body)
