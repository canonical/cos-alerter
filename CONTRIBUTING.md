# Contributing to COS Alerter

[Bugs](https://github.com/canonical/cos-alerter/issues)

[Pull Requests](https://github.com/canonical/cos-alerter/pulls)

## Setup

* `python3 -m venv venv`
* `source venv/bin/activate`

## Run

* `pip install .`
* `cos-alerter`

## Run With Docker
Prepare the image:
```shell
rockcraft pack
skopeo --insecure-policy copy oci-archive:cos-alerter_0.2.0_amd64.rock docker-daemon:cos-alerter:0.2.0
```

Run:
```shell
cp cos-alerter.sample.yaml cos-alerter.yaml
# Update cos-alerter.yaml with appropriate values
docker run -p 8080:8080 --rm --mount type=bind,source="$(pwd)"/cos-alerter.yaml,target=/etc/cos-alerter.yaml,readonly -it cos-alerter:0.2.0
```

## Run Tests

* `pip install tox`
* `tox`

## Build Packages

* `python3 -m build .`

