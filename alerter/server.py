import time
import tomllib

from flask import Flask

from . import DataWriter

app = Flask(__name__)
with open('/etc/cos-alerter.toml', 'rb') as f:
    app.config.update(tomllib.load(f))


@app.route('/alive', methods=['POST'])
def alive():
    # TODO Decide if we should validate the request.
    with DataWriter() as data:
        data.alert_time = time.time()
    return 'Success!'
