"""Run the daily booking scheduler inside another program (the web UI)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from typing import TYPE_CHECKING

from .scheduler import DaemonService, build_scheduler
from .state import StateStore

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)


class BackgroundDaemon:
    """The same scheduler as ``webtu daemon``, but in a thread that can be stopped."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        self._ready = threading.Event()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: Settings, store: StateStore) -> None:
        if self.running:
            return
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._thread_main,
            args=(settings, store),
            name="webetu-daemon",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=5)

    def stop(self) -> None:
        loop, stop = self._loop, self._stop
        if loop is not None and stop is not None:
            # If the loop already ended (the scheduler crashed) there is nothing to stop.
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(stop.set)
        if self._thread is not None:
            self._thread.join(timeout=10)
        self._thread = None
        self._loop = None
        self._stop = None

    def _thread_main(self, settings: Settings, store: StateStore) -> None:
        try:
            asyncio.run(self._main(settings, store))
        except Exception as exc:
            logger.error("le planificateur s'est arrêté: %s", type(exc).__name__)
        finally:
            self._ready.set()

    async def _main(self, settings: Settings, store: StateStore) -> None:
        stop = asyncio.Event()
        self._loop = asyncio.get_running_loop()
        self._stop = stop
        service = DaemonService(settings, store)
        scheduler = build_scheduler(settings, store, service.run)
        service.scheduler = scheduler
        scheduler.start()
        self._ready.set()
        try:
            await stop.wait()
        finally:
            scheduler.shutdown(wait=False)
