# COS Alerter
COS Alerter is intended to be used together with alertmanager and prometheus:
- Liveness of Alertmanager through an always-firing alert rule ("Watchdog")
- Liveness of COS Alerter itself from a metric endpoint it exposes and prometheus scrapes
## Configuring Alertmanager

Add the following sections to your Alertmanager config to integrate with COS Alerter:
```yaml
receivers:
...
- name: cos-alerter
  webhook_configs:
  - url: http://192.168.122.118:5000/alive
route:
  ...
  routes:
  ...
  - matchers:
    - alertname = Watchdog
    receiver: cos-alerter
    group_wait: 0s
    group_interval: 1m
    repeat_interval: 1m
```

## Run COS Alerter

* Copy the contents of `cos-alerter-default.yaml` to `cos-alerter.yaml` and fill in with correct values.
* `docker build . -t cos-alerter`
* `docker run -p 8080:8080 --mount type=bind,source="$(pwd)"/cos-alerter.yaml,target=/etc/cos-alerter.yaml,readonly -it cos-alerter`
