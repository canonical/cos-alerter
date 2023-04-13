# COS Alerter
COS Alerter is intended to be used together with alertmanager and prometheus:
- Liveness of Alertmanager through an always-firing alert rule ("Watchdog")
- Liveness of COS Alerter itself from a metric endpoint it exposes and prometheus scrapes
## Configuring Alertmanager

In order to integrate with COS Alerter you need to a heartbeat rule to Prometheus and Add a route to the Alertmanager config

If you are using the Canonical Observability Stack, the alert rule is already created for you. If not, you can use a rule similar to the following:
```yaml
- alert: Watchdog
  annotations:
    summary: A continuously firing alert that ensures Alertmanager is working correctly.
  expr: vector(1)
  labels:
    severity: none
```

Add the following to your alertmanager config to create the route:
```yaml
receivers:
...
- name: cos-alerter
  webhook_configs:
  - url: http://<cos-alerter-address>:8080/alive?clientid=<clientid>
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
Note that `group_wait` should be set to `0s` so the alert starts firing right away.


## Run COS Alerter

Coming soon...

See [CONTRIBUTING.md](CONTRIBUTING.md) for running development builds.
