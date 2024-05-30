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
cp config-defaults.yaml cos-alerter.yaml
# Update cos-alerter.yaml with appropriate values
docker run -p 8080:8080 --rm --mount type=bind,source="$(pwd)"/cos-alerter.yaml,target=/etc/cos-alerter.yaml,readonly -it cos-alerter:0.2.0
```

## Run With Kubernetes
Prepare the image:
```shell
rockcraft pack
# update <registry-ip> with the actual IP of your docker registry
# update <image-tag> with the image tag you would like to use in testing
skopeo copy oci-archive:cos-alerter_0.8.0_amd64.rock docker://<registry-ip>/<image-tag> --dest-tls-verify=false
```

Run:
```shell
# in k8s-local-test/deploy.yaml update <registry-ip>/<image-tag> with appropriate values
# in k8s-local-test/deploy.yaml update cos-alerter.yaml configmap with appropriate values
kubectl apply -f k8s-local-test/deploy.yaml
kubectl apply -f k8s-local-test/svc.yaml
```

## Run Tests

* `pip install tox`
* `tox`

## Build Packages

* `python3 -m build .`

