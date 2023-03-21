#!/usr/bin/env python3

import durationpy
import email
import json
import signal
import smtplib
import subprocess
import sys
import time

from alerter import DataWriter, conf, update_conf


def notify(time_data):
    # TODO: actually send email
    if not time.time() - time_data.notify_time > durationpy.from_str(conf['notify']['repeat_interval']).total_seconds():
        #TODO log something here
        return
    time_data.notify_time = time.time()
    print("Alertmanager down! Sending mail.")


def sighup(_, __):
    update_conf()


def send_test_mail(_, __):
    msg = email.message.EmailMessage()
    msg['Subject'] = 'cos-alerter test email'
    msg['From'] = conf['notify']['send_address']
    msg['To'] = ', '.join(conf['notify']['recipients'])
    msg.set_content('This is a test email from COS Alerter.')
    server = smtplib.SMTP_SSL(host=conf['notify']['smtp_address'], port=conf['notify']['smtp_ssl_port'])
    server.login(user=conf['notify']['smtp_username'], password=conf['notify']['smtp_password'])
    server.sendmail(from_addr=conf['notify']['send_address'], to_addrs=', '.join(conf['notify']['recipients']), msg=msg.as_string())
    return "<p>Hello, World!</p>"


def sigint(_, __):
    sys.exit()


def main():

    update_conf()

    # Create the initial data file
    with open(conf['watcher']['data_file'], 'w') as f:
        json.dump({'alert_time': time.time(), 'notify_time': 0.0}, f)

    signal.signal(signal.SIGINT, sigint)
    signal.signal(signal.SIGHUP, sighup)
    signal.signal(signal.SIGUSR1, send_test_mail)

    subprocess.Popen(['flask', '--app', 'root.alerter.server', 'run', '--host', '0.0.0.0'])

    while(True):
        with DataWriter() as time_data:
            if time.time() - time_data.alert_time > durationpy.from_str(conf['watcher']['down_interval']).total_seconds():
                notify(time_data)


if __name__ == '__main__':
    main()
