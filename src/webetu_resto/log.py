"""Logging setup shared by the CLI, the daemon and the Telegram bot.

``httpx`` logs every request URL at INFO level. Resto URLs contain a JWT in the
``token`` query parameter, and Telegram URLs contain the bot token in the path,
so those loggers are forced to WARNING to keep credentials out of logs.
"""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_NOISY_LOGGERS = ("httpx", "httpcore")


def configure_logging(level: str | int = "INFO") -> None:
    """Configure root logging without ever emitting request URLs."""
    if isinstance(level, str):
        resolved = getattr(logging, level.upper(), logging.INFO)
    else:
        resolved = level
    logging.basicConfig(level=resolved, format=_LOG_FORMAT)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
