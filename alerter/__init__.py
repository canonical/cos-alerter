import fcntl
import json
import tomllib

config = {}

class Conf:
    def __getitem__(self, key):
        return config[key]

conf = Conf()

def update_conf():
    global config
    with open('/etc/cos-alerter.toml', 'rb') as f:
        config = tomllib.load(f)


class DataWriter:

    def __enter__(self):
        self.fh = open(config['watcher']['data_file'], 'r+')
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
