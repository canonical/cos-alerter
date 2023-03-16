import pathlib
import pprint
import tomllib

from email.message import EmailMessage
from flask import Flask, request

app = Flask(__name__)
with open('/etc/cos-alerter.toml', 'rb') as f:
    app.config.update(tomllib.load(f))

@app.route('/alive', methods=['POST'])
def alive():
    content = request.json
    #if content['commonLabels']['alertname'] == 'Watchdog':
    #    pathlib.path('/var/lib/cos-alerter.txt').touch()

    pprint.pprint(content)
    return 'Success!'
