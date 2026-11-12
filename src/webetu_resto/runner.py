"""Orchestration: login, resolve the restaurant, plan, book, report."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo

from .booking import apply_results, plan_reservations, resolve_depot, target_dates
from .client import PROGRES_BASE, RESTO_BASE, WebetuClient
from .models import Depot, Reservation, RunReport, StudentContext
from .signing import DEFAULT_HMAC_SECRET
from .state import StateStore, effective_meals, effective_resto_id

logger = logging.getLogger(__name__)

ClientFactory = Callable[..., WebetuClient]


@dataclass(slots=True)
class RunOptions:
    username: str
    password: str
    resto_id: int | None = None
    book_days: list[int] = field(default_factory=lambda: [1, 2, 3])
    meals: list[int] = field(default_factory=lambda: [1, 2, 3])
    timezone: str = "Africa/Algiers"
    progres_base: str = PROGRES_BASE
    resto_base: str = RESTO_BASE
    hmac_secret: str = DEFAULT_HMAC_SECRET
    request_interval: float = 0.3
    dry_run: bool = False
    today: date | None = None
    target_days: list[date] | None = None


@dataclass(slots=True)
class Snapshot:
    context: StudentContext
    depot: Depot
    depots: list[Depot]
    reservations: list[Reservation]


def _now(options: RunOptions) -> datetime:
    tz: tzinfo
    try:
        tz = ZoneInfo(options.timezone)
    except Exception:
        tz = UTC
    return datetime.now(tz)


def _build_client(options: RunOptions, factory: ClientFactory) -> WebetuClient:
    return factory(
        username=options.username,
        password=options.password,
        progres_base=options.progres_base,
        resto_base=options.resto_base,
        hmac_secret=options.hmac_secret,
        request_interval=options.request_interval,
    )


def fetch_snapshot(options: RunOptions, *, factory: ClientFactory = WebetuClient) -> Snapshot:
    """Read-only view used by `webtu status` and the bot dashboard."""
    client = _build_client(options, factory)
    try:
        client.login()
        client.load_student_context()
        client.ensure_resto_session()
        depots = client.get_depots()
        depot = resolve_depot(depots, options.resto_id)
        reservations = client.list_reservations()
        context = client.session
        assert context is not None
        return Snapshot(
            context=context,
            depot=depot,
            depots=depots,
            reservations=reservations,
        )
    finally:
        client.close()


def run_once(options: RunOptions, *, factory: ClientFactory = WebetuClient) -> RunReport:
    """Run one idempotent booking pass over the rolling window."""
    started_at = _now(options)
    today = options.today or started_at.date()
    days = (
        sorted(set(options.target_days))
        if options.target_days
        else target_dates(today, options.book_days)
    )

    report = RunReport(started_at=started_at, dates=days, dry_run=options.dry_run)
    client = _build_client(options, factory)
    try:
        client.login()
        client.load_student_context()
        client.ensure_resto_session()

        depots = client.get_depots()
        depot = resolve_depot(depots, options.resto_id)
        report.depot = depot

        existing = client.list_reservations()
        plan = plan_reservations(
            existing,
            days,
            options.meals,
            depot,
            today=today,
        )
        report.planned = plan.items
        report.skipped = plan.skipped
        report.warnings = plan.warnings

        if options.dry_run or not plan.items:
            return report

        logger.info(
            "réservation de %d repas à %s pour %s",
            len(plan.items),
            depot.label,
            ", ".join(day.isoformat() for day in days),
        )
        results = client.reserve(plan.items)
        report.booked, report.failed = apply_results(plan.items, results)
        return report
    finally:
        client.close()


def options_from_settings(
    settings: Any,
    *,
    meals: list[int] | None = None,
    resto_id: int | None = None,
    book_days: list[int] | None = None,
    dry_run: bool | None = None,
    today: date | None = None,
    target_days: list[date] | None = None,
) -> RunOptions:
    """Build RunOptions from Settings without importing it (avoids a cycle)."""
    return RunOptions(
        username=settings.webetu_username,
        password=settings.password,
        resto_id=resto_id if resto_id is not None else settings.webetu_resto_id,
        book_days=book_days if book_days is not None else settings.book_days,
        meals=meals if meals is not None else settings.meals,
        timezone=settings.webetu_timezone,
        progres_base=settings.webetu_progres_base,
        resto_base=settings.webetu_resto_base,
        hmac_secret=settings.hmac_secret,
        request_interval=settings.webetu_request_interval,
        dry_run=settings.webetu_dry_run if dry_run is None else dry_run,
        today=today,
        target_days=target_days,
    )


def run_with_prefs(
    settings: Any,
    store: StateStore,
    *,
    target_days: list[date] | None = None,
    dry_run: bool | None = None,
    meals: list[int] | None = None,
    resto_id: int | None = None,
) -> RunReport:
    """Run once using the preferences stored by the bot (meals, resto, auto)."""
    state = store.load()
    options = options_from_settings(
        settings,
        meals=meals if meals is not None else effective_meals(settings.meals, state),
        resto_id=(
            resto_id
            if resto_id is not None
            else effective_resto_id(settings.webetu_resto_id, state)
        ),
        dry_run=dry_run,
        target_days=target_days,
    )
    report = run_once(options)
    if not report.dry_run:
        store.record_run(report)
    return report
