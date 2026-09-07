"""Centralized safe logging configuration."""

import logging
from logging.handlers import RotatingFileHandler

from .config import (
    BASE_DIR,
    LOG_DIRECTORY,
    CLIENT_LOG_FILE,
    DISCOVERY_SERVER_LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)

_CONFIGURED = False


def _handler(path):
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )

    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )

    return handler


def setup_logging():
    global _CONFIGURED

    if _CONFIGURED:
        return

    level = getattr(
        logging,
        str(LOG_LEVEL).upper(),
        logging.INFO,
    )

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        root.addHandler(
            _handler(
                BASE_DIR
                / LOG_DIRECTORY
                / CLIENT_LOG_FILE
            )
        )

    discovery_logger = logging.getLogger("discovery_server")
    discovery_logger.setLevel(level)
    discovery_logger.propagate = False

    if not discovery_logger.handlers:
        discovery_logger.addHandler(
            _handler(
                BASE_DIR
                / LOG_DIRECTORY
                / DISCOVERY_SERVER_LOG_FILE
            )
        )

    _CONFIGURED = True


def get_logger(name=None):
    setup_logging()
    return logging.getLogger(name)


def get_discovery_server_logger():
    setup_logging()
    return logging.getLogger("discovery_server")