"""APScheduler wiring: daily run, periodic auto-check, catch-up and retries."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .errors import WebetuError
from .formatting import format_report
from .runner import run_with_prefs
from .schedule import needs_catch_up, next_run_at, retry_delay_seconds
from .state import StateStore

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)

Job = Callable[[], Awaitable[None]]


def build_scheduler(settings: Settings, store: StateStore, job: Job) -> AsyncIOScheduler:
    timezone = settings.timezone
    scheduler = AsyncIOScheduler(timezone=timezone)
    hour, minute = settings.run_at_parts
    scheduler.add_job(
        job,
        CronTrigger(hour=hour, minute=minute, timezone=timezone),
        id="daily-booking",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )

    interval = settings.webetu_check_interval_minutes
    if interval > 0:
        scheduler.add_job(
            job,
            IntervalTrigger(minutes=interval, timezone=timezone),
            id="auto-check",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=600,
        )

    state = store.load()
    today = datetime.now(timezone).date()
    last = state.last_run
    if last is None or needs_catch_up(last.day, today) or last.status in {"failed", "partial"}:
        scheduler.add_job(
            job,
            DateTrigger(run_date=datetime.now(timezone) + timedelta(seconds=10)),
            id="catch-up",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
    return scheduler


class DaemonService:
    """Runs the idempotent booking pass for the daemon: daily, auto-check and retries."""

    def __init__(self, settings: Settings, store: StateStore) -> None:
        self.settings = settings
        self.store = store
        self.scheduler: AsyncIOScheduler | None = None
        self._retries: dict[str, int] = {}

    def _day_key(self) -> str:
        return datetime.now(self.settings.timezone).date().isoformat()

    def next_run(self) -> datetime | None:
        """When the next daily pass is planned (None before the scheduler starts)."""
        if self.scheduler is None:
            return None
        job = self.scheduler.get_job("daily-booking")
        return getattr(job, "next_run_time", None)

    async def run(self) -> None:
        await self._run_once()
        upcoming = self.next_run()
        if upcoming is not None:
            logger.info("prochain passage prévu: %s", upcoming.strftime("%Y-%m-%d %H:%M"))

    async def _run_once(self) -> None:
        if not self.store.load().prefs.auto:
            logger.info("mode automatique désactivé, passage ignoré")
            return
        try:
            report = await asyncio.to_thread(run_with_prefs, self.settings, self.store)
        except WebetuError as exc:
            logger.error("passage échoué: %s", exc)
            self._schedule_retry()
            return

        if report.booked or report.failed:
            logger.info(
                "passage %s: %d réservés, %d échecs",
                report.status,
                len(report.booked),
                len(report.failed),
            )
            print(format_report(report), flush=True)
        else:
            logger.info("vérification: tout est déjà réservé (%d repas)", len(report.skipped))

        if report.failed:
            self._schedule_retry()
        else:
            self._retries.pop(self._day_key(), None)

    def _schedule_retry(self) -> None:
        if self.scheduler is None:
            return
        key = self._day_key()
        used = self._retries.get(key, 0)
        if used >= max(0, self.settings.webetu_max_retries):
            logger.warning("plus de tentative de retry aujourd'hui")
            return
        self._retries[key] = used + 1
        delay = retry_delay_seconds(used, self.settings.webetu_retry_delay)
        run_at = datetime.now(self.settings.timezone) + timedelta(seconds=delay)
        self.scheduler.add_job(
            self.run,
            DateTrigger(run_date=run_at),
            id=f"retry-{key}-{used}",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
        logger.info("nouvelle tentative dans %ss", delay)


async def _run_cli_daemon(settings: Settings, store: StateStore) -> None:
    service = DaemonService(settings, store)
    scheduler = build_scheduler(settings, store, service.run)
    service.scheduler = scheduler
    scheduler.start()
    interval = settings.webetu_check_interval_minutes
    logger.info(
        "daemon actif — prochain passage: %s, vérification auto: %s",
        next_run_at(datetime.now(settings.timezone), settings.webetu_run_at),
        f"toutes les {interval} min" if interval else "désactivée",
    )
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


def run_cli_daemon(settings: Settings, store: StateStore) -> None:
    try:
        asyncio.run(_run_cli_daemon(settings, store))
    except KeyboardInterrupt:
        logger.info("daemon arrêté")
