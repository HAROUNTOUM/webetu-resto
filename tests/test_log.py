from __future__ import annotations

import logging

from webetu_resto.log import configure_logging


def test_http_loggers_are_quiet() -> None:
    configure_logging("DEBUG")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_unknown_level_falls_back_to_info() -> None:
    configure_logging("not-a-level")
    assert logging.getLogger("httpx").level == logging.WARNING
