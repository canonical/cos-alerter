from flask import Flask

from .alerter import AlerterState

app = Flask(__name__)


@app.route('/alive', methods=['POST'])
def alive():
    # TODO Decide if we should validate the request.
    with AlerterState() as state:
        state.set_alert_time()
    return 'Success!'
