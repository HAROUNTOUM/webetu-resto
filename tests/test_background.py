from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

from webetu_resto import background
from webetu_resto.background import BackgroundDaemon


class FakeScheduler:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = True) -> None:
        self.stopped = True


class FakeService:
    def __init__(self, settings: Any, store: Any) -> None:
        self.scheduler: Any = None

    async def run(self) -> None:
        return None


def _wait_for(condition: Any, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


def test_daemon_starts_and_stops_cleanly(monkeypatch) -> None:
    scheduler = FakeScheduler()
    monkeypatch.setattr(background, "DaemonService", FakeService)
    monkeypatch.setattr(background, "build_scheduler", lambda settings, store, job: scheduler)
    daemon = BackgroundDaemon()
    assert daemon.running is False
    daemon.start(SimpleNamespace(), SimpleNamespace())
    assert daemon.running is True
    assert scheduler.started is True
    daemon.start(SimpleNamespace(), SimpleNamespace())  # second start is ignored
    daemon.stop()
    assert _wait_for(lambda: scheduler.stopped)
    assert daemon.running is False


def test_daemon_survives_a_scheduler_that_cannot_start(monkeypatch) -> None:
    def broken(settings: Any, store: Any, job: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(background, "DaemonService", FakeService)
    monkeypatch.setattr(background, "build_scheduler", broken)
    daemon = BackgroundDaemon()
    daemon.start(SimpleNamespace(), SimpleNamespace())
    assert _wait_for(lambda: not daemon.running)
    daemon.stop()  # stopping a dead daemon is harmless
