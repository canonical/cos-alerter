# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import os

import pytest
import yaml
from helpers import CONFIG

from cos_alerter.alerter import __file__ as alerter_file
from cos_alerter.alerter import config

DEFAULT_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.realpath(alerter_file)), "config-defaults.yaml"
)
with open(DEFAULT_CONFIG_FILE) as f:
    DEFAULT_CONFIG = f.read()


@pytest.fixture
def fake_fs(fs):
    fs.create_file(DEFAULT_CONFIG_FILE)
    with open(DEFAULT_CONFIG_FILE, "w") as f:
        f.write(DEFAULT_CONFIG)
    fs.create_file("/etc/cos-alerter.yaml")
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(yaml.dump(CONFIG))
    config.set_path("/etc/cos-alerter.yaml")
    config.reload()
    return fs
