# COS Alerter

[![Push to Main](https://github.com/canonical/cos-alerter/actions/workflows/push-main.yaml/badge.svg)](https://github.com/canonical/cos-alerter/actions/workflows/push-main.yaml)
[![Release Snap](https://github.com/canonical/cos-alerter/actions/workflows/release-snap.yaml/badge.svg)](https://github.com/canonical/cos-alerter/actions/workflows/release-snap.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

COS Alerter is intended to be used together with alertmanager and prometheus:
- Liveness of Alertmanager through an always-firing alert rule ("Watchdog")
- Liveness of COS Alerter itself from a metric endpoint it exposes and prometheus scrapes
## Configuring Alertmanager

In order to integrate with COS Alerter you need to add a heartbeat rule to Prometheus and add a route to the Alertmanager config.

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
  - url: http://<cos-alerter-address>:8080/alive?clientid=<clientid>&key=<clientkey>
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

## Configuring COS Alerter

Copy the file `cos_alerter/config-defaults.yaml` to `/etc/cos-alerter.yaml` (If running without docker) or `./cos-alerter` (if running with docker). Edit the file with the appropriate values for your environment.

## Running COS Alerter

### Docker

The easiest way to run COS Alerter is to use docker.
```
docker run -p 8080:8080 --mount type=bind,source="$(pwd)"/cos-alerter.yaml,target=/etc/cos-alerter.yaml,readonly -it ghcr.io/canonical/cos-alerter:latest
```

### Python

You can also run cos-alerter by installing the python package.
```
pip install cos-alerter
cos-alerter
```

### Development Builds

See [CONTRIBUTING.md](CONTRIBUTING.md) for running development builds.
