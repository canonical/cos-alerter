#!/usr/bin/env python3

import signal
import subprocess
import sys
import time

from .alerter import AlerterState, send_notifications


def send_test_mail(_, __):
    send_notifications(title='COS-Alerter test email.', body='This is a test email automatically generated by COS-alerter.')


def sigint(_, __):
    sys.exit()


def main():

    AlerterState.initialize()

    signal.signal(signal.SIGINT, sigint)
    signal.signal(signal.SIGUSR1, send_test_mail)

    subprocess.Popen(['waitress-serve', 'cos_alerter.server:app'])

    while(True):
        with AlerterState() as state:
            if state.is_down():
                state.notify()
        time.sleep(1)


if __name__ == '__main__':
    main()
