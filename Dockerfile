FROM python:3.11
ADD ./cos_alerter /root/cos_alerter
ADD ./pyproject.toml /root/
ADD ./LICENSE /root/
ADD ./README.md /root/
ADD ./cos-alerter-default.yaml /etc/cos-alerter.yaml
RUN pip install /root
CMD ["cos-alerter"]
