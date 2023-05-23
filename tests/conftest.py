# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import os

import pytest
import yaml
from helpers import CONFIG

from cos_alerter.alerter import __file__ as alerter_file
from cos_alerter.alerter import config

ALERTER_PATH = os.path.dirname(os.path.realpath(alerter_file))


@pytest.fixture
def fake_fs(fs):
    default_config_file = os.path.join(ALERTER_PATH, "config-defaults.yaml")
    fs.pause()
    with open(default_config_file) as f:
        contents = f.read()
    fs.resume()
    fs.create_file(default_config_file)
    with open(default_config_file, "w") as f:
        f.write(contents)

    fs.create_file("/etc/cos-alerter.yaml")
    with open("/etc/cos-alerter.yaml", "w") as f:
        f.write(yaml.dump(CONFIG))
    config.set_path("/etc/cos-alerter.yaml")

    fs.pause()
    templates = os.listdir(os.path.join(ALERTER_PATH, "templates"))
    for template in templates:
        template_path = os.path.join(ALERTER_PATH, f"templates/{template}")
        with open(template_path) as f:
            template_contents = f.read()
        fs.resume()
        fs.create_file(template_path)
        with open(template_path, "w") as f:
            f.write(template_contents)
        fs.pause()
    fs.resume()

    config.reload()
    return fs
