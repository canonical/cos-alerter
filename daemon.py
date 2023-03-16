#!/usr/bin/env python3

import durationpy
import email
import pathlib
import signal
import smtplib
import subprocess
import sys
import time
import tomllib

conf = {}

def send_mail():
    # TODO: actually send email
    print("Alertmanager down! Sending mail.")

def update_conf(_, __):
    global conf
    with open('/etc/cos-alerter.toml', 'rb') as f:
        conf = tomllib.load(f)

def send_test_mail(_, __):
    msg = email.message.EmailMessage()
    msg['Subject'] = 'cos-alerter test email'
    msg['From'] = conf['alerter']['send_address']
    msg['To'] = ', '.join(conf['alerter']['recipients'])
    msg.set_content('This is a test email from COS Alerter.')
    server = smtplib.SMTP_SSL(host=conf['alerter']['smtp_address'], port=conf['alerter']['smtp_ssl_port'])
    server.login(user=conf['alerter']['smtp_username'], password=conf['alerter']['smtp_password'])
    server.sendmail(from_addr=conf['alerter']['send_address'], to_addrs=', '.join(conf['alerter']['recipients']), msg=msg.as_string())
    return "<p>Hello, World!</p>"

def sigint(_, __):
    sys.exit()

def main():

    # Write to the time file once at start so we can start checking immediately.
    pathlib.Path('/var/lib/cos-alerter.txt').touch()

    update_conf(None, None)

    signal.signal(signal.SIGINT, sigint)
    signal.signal(signal.SIGHUP, update_conf)
    signal.signal(signal.SIGUSR1, send_test_mail)

    server_proc = subprocess.Popen(['flask', '--app', 'root.server', 'run', '--host', '0.0.0.0'])

    while(True):
        mod_time = pathlib.Path('/var/lib/cos-alerter.txt').stat().st_mtime
        if time.time() - mod_time > durationpy.from_str(conf['watcher']['down_interval']).total_seconds():
            send_mail()


if __name__ == '__main__':
    main()
