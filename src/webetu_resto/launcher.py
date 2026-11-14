"""Entry point of the Windows program (double-click).

With no arguments it opens the local web interface. A windowed program has no
console, so output is redirected to a small log file in the config folder.
"""

from __future__ import annotations

import os
import sys

from .paths import config_dir

LOG_NAME = "webetu-resto.log"
MAX_LOG_BYTES = 1_000_000


def ensure_streams() -> None:
    """Give stdout/stderr/stdin a target when Windows provides none."""
    if sys.stdout is not None and sys.stderr is not None and sys.stdin is not None:
        return
    try:
        log = config_dir() / LOG_NAME
        log.parent.mkdir(parents=True, exist_ok=True)
        if log.exists() and log.stat().st_size > MAX_LOG_BYTES:
            log.unlink()
        stream = open(log, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    except OSError:
        stream = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
    if sys.stdin is None:
        sys.stdin = open(os.devnull, encoding="utf-8")  # noqa: SIM115


def main() -> None:
    ensure_streams()
    from .cli import app

    if len(sys.argv) == 1:
        sys.argv.append("ui")
    app()
