FROM python:3.11
ADD ./daemon.py /root/daemon.py
ADD ./alerter /root/alerter
ADD ./requirements.txt /root/requirements.txt
ADD ./cos-alerter-default.toml /etc/cos-alerter.toml
RUN pip install -r /root/requirements.txt
CMD ["python3", "/root/daemon.py"]
