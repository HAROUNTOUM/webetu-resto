"""Quick self-check used when building the Windows program.

It starts the real scheduler and the real web server for a moment, so a
missing library in the packaged program is caught before a release is
published. Nothing is sent to ONOU.
"""

from __future__ import annotations

import http.client
import json
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast


def _check_timezone() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    datetime.now(ZoneInfo("Africa/Algiers"))


def _check_trigger() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from apscheduler.triggers.cron import CronTrigger

    tz = ZoneInfo("Africa/Algiers")
    trigger = CronTrigger(hour=0, minute=5, timezone=tz, jitter=300)
    if trigger.get_next_fire_time(None, datetime.now(tz)) is None:
        raise RuntimeError("cron trigger gave no fire time")


def _check_daemon() -> None:
    from pydantic import SecretStr

    from .background import BackgroundDaemon
    from .config import Settings
    from .state import StateStore

    with tempfile.TemporaryDirectory() as folder:
        settings = Settings.model_construct(
            webetu_username="selftest",
            webetu_password=SecretStr("selftest"),
            webetu_state_path=Path(folder) / "state.json",
        )
        daemon = BackgroundDaemon()
        daemon.start(settings, StateStore(settings.webetu_state_path))
        if not daemon.running:
            raise RuntimeError("scheduler did not start")
        daemon.stop()


def _check_server() -> None:
    from .ui import APP_ID, UiServer

    class _Nothing:
        pass

    server = UiServer(cast(Any, _Nothing()), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        connection.request("GET", "/api/ping")
        data = json.loads(connection.getresponse().read().decode("utf-8"))
        connection.close()
        if data.get("app") != APP_ID:
            raise RuntimeError("unexpected ping answer")
    finally:
        server.shutdown()
        server.server_close()


CHECKS: list[tuple[str, Callable[[], None]]] = [
    ("timezone data", _check_timezone),
    ("scheduler triggers", _check_trigger),
    ("background scheduler", _check_daemon),
    ("local web server", _check_server),
]


def run_selftest() -> list[str]:
    """Run every check and return the list of problems (empty = all good)."""
    problems: list[str] = []
    for name, check in CHECKS:
        try:
            check()
        except Exception as exc:
            problems.append(f"{name}: {type(exc).__name__}: {exc}")
    return problems
