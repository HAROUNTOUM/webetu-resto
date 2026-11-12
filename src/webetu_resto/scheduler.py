"""APScheduler wiring: daily run and catch-up."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .errors import WebetuError
from .formatting import format_report
from .runner import run_with_prefs
from .schedule import needs_catch_up, next_run_at
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


async def _daemon_job(settings: Settings, store: StateStore) -> None:
    try:
        report = await asyncio.to_thread(run_with_prefs, settings, store)
    except WebetuError as exc:
        logger.error("passage échoué: %s", exc)
        return
    logger.info(
        "passage %s: %d réservés, %d échecs",
        report.status,
        len(report.booked),
        len(report.failed),
    )
    print(format_report(report), flush=True)


async def _run_cli_daemon(settings: Settings, store: StateStore) -> None:
    async def job() -> None:
        await _daemon_job(settings, store)

    scheduler = build_scheduler(settings, store, job)
    scheduler.start()
    logger.info(
        "daemon actif — prochain passage: %s",
        next_run_at(datetime.now(settings.timezone), settings.webetu_run_at),
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
