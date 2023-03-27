import time
import yaml

from flask import Flask

from .alerter import AlerterState

app = Flask(__name__)
with open('/etc/cos-alerter.yaml', 'rb') as f:
    app.config.update(yaml.safe_load(f))


@app.route('/alive', methods=['POST'])
def alive():
    # TODO Decide if we should validate the request.
    with AlerterState() as data:
        data.alert_time = time.time()
    return 'Success!'
