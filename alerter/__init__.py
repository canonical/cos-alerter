import fcntl
import json
import tomllib

import apprise

conf = {}


class Config:
    def __getitem__(self, key):
        return conf[key]


config = Config()


def update_config():
    global conf
    with open('/etc/cos-alerter.toml', 'rb') as f:
        conf = tomllib.load(f)


class DataWriter:

    def __enter__(self):
        self.fh = open(conf['watch']['data_file'], 'r+')
        fcntl.lockf(self.fh, fcntl.LOCK_EX)
        self.data = json.load(self.fh)
        return self

    def __exit__(self, _, __, ___):
        self.fh.seek(0)
        json.dump(self.data, self.fh)
        self.fh.truncate()
        fcntl.lockf(self.fh, fcntl.LOCK_UN)
        self.fh.close()

    @property
    def alert_time(self):
        return self.data['alert_time']

    @alert_time.setter
    def alert_time(self, value):
        self.data['alert_time'] = value

    @property
    def notify_time(self):
        return self.data['notify_time']

    @notify_time.setter
    def notify_time(self, value):
        self.data['notify_time'] = value


def send_notifications(title, body):
    sender = apprise.Apprise()
    for source in conf['notify']['destinations']:
        sender.add(source)
    sender.notify(title=title, body=body)
