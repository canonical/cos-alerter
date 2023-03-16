# COS Alerter

## Configuring Alertmanager

Add the following sections to your Alertmanager config integrate with COS Alerter:
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

* Copy the contents of `cos-alerter-default.toml` to `cos-alerter.toml` and fill in with correct values.
* `docker build . -t cos-alerter`
* `docker run -p 5000:5000 --mount type=bind,source="$(pwd)"/cos-alerter.toml,target=/etc/cos-alerter.toml,readonly -it cos-alerter`
