"""Centralized logging configuration for the P2P Chat project.

Usage:
    from Code.P2PChat.src.logging_config import configure_logging
    configure_logging()

The configuration writes logs to both the console and a rotating file.
It is safe to call more than once.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "p2pchat.log"
DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"


def configure_logging(
    level: int = logging.INFO,
    log_file: str | Path = DEFAULT_LOG_FILE,
    console: bool = True,
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
) -> logging.Logger:
    """Configure project-wide console + rotating-file logging."""
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(DEFAULT_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    target = Path(log_file)
    target.parent.mkdir(parents=True, exist_ok=True)

    existing_files = {
        Path(getattr(h, "baseFilename", "")).resolve()
        for h in root.handlers
        if isinstance(h, RotatingFileHandler)
    }
    if target.resolve() not in existing_files:
        file_handler = RotatingFileHandler(
            target, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if console and not any(getattr(h, "_p2p_console", False) for h in root.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler._p2p_console = True
        root.addHandler(console_handler)

    return logging.getLogger("p2pchat")


def set_log_level(level: int | str) -> None:
    """Change the level for the configured root logger at runtime."""
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logging.getLogger().setLevel(level)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)


__all__ = ["configure_logging", "set_log_level", "DEFAULT_LOG_FILE"]
