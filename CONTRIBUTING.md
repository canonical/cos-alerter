# Contributing to COS Alerter

[Bugs](https://github.com/canonical/cos-alerter/issues)
[Pull Requests](https://github.com/canonical/cos-alerter/pulls)

## Setup

* `python3 -m venv venv`
* `source venv/bin/activate`

## Run

* `pip install .`
* `cos-alerter`

## Run Tests

* `pip install tox`
* `tox`

## Run With Docker

* Copy the contents of `cos-alerter-default.yaml` to `cos-alerter.yaml` and fill in with appropiate values.
* `docker build . -t cos-alerter`
* `docker run -p 8080:8080 --mount type=bind,source="$(pwd)"/cos-alerter.yaml,target=/etc/cos-alerter.yaml,readonly -it cos-alerter`

## Build Packages

* `python3 -m build .`

