import datetime
import fcntl
import json
import textwrap
import threading
import time
import yaml

import apprise
import durationpy


class Config:
    def __getitem__(self, key):
        with open('/etc/cos-alerter.yaml', 'rb') as f:
            return yaml.safe_load(f)[key]


config = Config()


class AlerterState:

    def __enter__(self):
        self.fh = open(config['watch']['data_file'], 'r+')
        fcntl.lockf(self.fh, fcntl.LOCK_EX)
        self.data = json.load(self.fh)
        return self

    def __exit__(self, _, __, ___):
        self.fh.seek(0)
        json.dump(self.data, self.fh)
        self.fh.truncate()
        fcntl.lockf(self.fh, fcntl.LOCK_UN)
        self.fh.close()

    @staticmethod
    def initialize():
        # Note this method does not do any locking so be responsible.
        current_date = datetime.datetime.now(datetime.timezone.utc)
        current_time = time.monotonic()
        data = {
            # The actual date and time that COS Alerter was started.
            'start_date': datetime.datetime.timestamp(current_date),

            # The time according to the monotonic clock that COS Alerter was started.
            'start_time': current_time,

            # The last time we received an alert from Alertmanager.
            'alert_time': current_time,

            # The last time we sent out notifications.
            'notify_time': None,
        }

        with open(config['watch']['data_file'], 'w') as f:
            json.dump(data, f)

    def set_alert_time(self):
        self.data['alert_time'] = time.monotonic()

    def _set_notify_time(self):
        self.data['notify_time'] = time.monotonic()

    def is_down(self):
        down_interval = durationpy.from_str(config['watch']['down_interval']).total_seconds()
        return time.monotonic() - self.data['alert_time'] > down_interval

    def _recently_notified(self):
        repeat_interval = durationpy.from_str(config['notify']['repeat_interval']).total_seconds()
        return self.data['notify_time'] and not time.monotonic() - self.data['notify_time'] > repeat_interval

    def _last_alert_datetime(self):
        actual_alert_timestamp = (self.data['alert_time'] - self.data['start_time']) + self.data['start_date']
        return datetime.datetime.fromtimestamp(actual_alert_timestamp, datetime.timezone.utc)

    def notify(self):
        # If we have already notified recently, do nothing.
        if self._recently_notified():
            return

        self._set_notify_time()
        actual_alert_timestamp = (self.data['alert_time'] - self.data['start_time']) + self.data['start_date']
        last_alert_time = self._last_alert_datetime().isoformat()
        title = '**Alertmanager is Down!**'
        body = textwrap.dedent(f'''
            Your Alertmanager instance seems to be down!
            It has not alerted COS-Alerter since {last_alert_time} UTC.
            ''')

        # Sending notifications can be a long operation so handle that in a separate thread.
        notify_thread = threading.Thread(target=send_notifications, kwargs={'title': title, 'body': body})
        notify_thread.start()


def send_notifications(title, body):
    # TODO: Since this is run in it's own thread, we have to make sure we properly
    # log failures here.
    sender = apprise.Apprise()
    for source in config['notify']['destinations']:
        sender.add(source)
    sender.notify(title=title, body=body)
