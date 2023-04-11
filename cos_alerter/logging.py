# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Logging related functions."""

import logging

from .alerter import config

LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "critical": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "error": logging.ERROR,
    "WARNING": logging.WARNING,
    "warning": logging.WARNING,
    "INFO": logging.INFO,
    "info": logging.INFO,
    "DEBUG": logging.DEBUG,
    "debug": logging.DEBUG,
}


def init_logging(args):
    """Initialize the loggers."""
    log_level = LEVELS[config["log_level"]]
    if args.log_level:
        log_level = LEVELS[args.log_level]
    cos_logger = logging.getLogger("cos_alerter")
    waitress_logger = logging.getLogger("waitress")
    cos_logger.propagate = False
    waitress_logger.propagate = False
    cos_logger.setLevel(level=log_level)
    waitress_logger.setLevel(level=log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")
    handler.setFormatter(formatter)
    cos_logger.addHandler(handler)
    waitress_logger.addHandler(handler)
