from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest

from webetu_resto.config import Settings
from webetu_resto.errors import WebetuError
from webetu_resto.models import BookingItem, RunReport
from webetu_resto.scheduler import DaemonService, build_scheduler
from webetu_resto.state import LastRun, Prefs, State, StateStore


def _settings(tmp_path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "webetu_username": "123456789",
        "webetu_password": "secret",
        "webetu_max_retries": 2,
        "webetu_retry_delay": 1,
        "webetu_state_path": tmp_path / "state.json",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


async def _job() -> None:
    return None


async def test_build_scheduler_adds_daily_and_catch_up(tmp_path) -> None:
    settings = _settings(tmp_path)
    store = StateStore(settings.webetu_state_path)
    scheduler = build_scheduler(settings, store, _job)
    scheduler.start(paused=True)
    try:
        ids = {job.id for job in scheduler.get_jobs()}
    finally:
        scheduler.shutdown(wait=False)
    assert ids == {"daily-booking", "catch-up"}


async def test_build_scheduler_skips_catch_up_after_success(tmp_path) -> None:
    settings = _settings(tmp_path)
    store = StateStore(settings.webetu_state_path)
    today = datetime.now(settings.timezone).date().isoformat()
    store.save(State(last_run=LastRun(today, "ok", 3, 0, 0, f"{today}T00:05:00")))
    scheduler = build_scheduler(settings, store, _job)
    scheduler.start(paused=True)
    try:
        ids = {job.id for job in scheduler.get_jobs()}
    finally:
        scheduler.shutdown(wait=False)
    assert ids == {"daily-booking"}


async def test_build_scheduler_catches_up_after_failure(tmp_path) -> None:
    settings = _settings(tmp_path)
    store = StateStore(settings.webetu_state_path)
    today = datetime.now(settings.timezone).date().isoformat()
    store.save(State(last_run=LastRun(today, "failed", 0, 0, 1, f"{today}T00:05:00")))
    scheduler = build_scheduler(settings, store, _job)
    scheduler.start(paused=True)
    try:
        ids = {job.id for job in scheduler.get_jobs()}
    finally:
        scheduler.shutdown(wait=False)
    assert "catch-up" in ids


@pytest.mark.parametrize("status", ["partial", "failed"])
async def test_catch_up_for_non_ok_statuses(tmp_path, status: str) -> None:
    settings = _settings(tmp_path)
    store = StateStore(settings.webetu_state_path)
    today = datetime.now(settings.timezone).date().isoformat()
    store.save(State(last_run=LastRun(today, status, 0, 0, 1, f"{today}T00:05:00")))
    scheduler = build_scheduler(settings, store, _job)
    scheduler.start(paused=True)
    try:
        ids = {job.id for job in scheduler.get_jobs()}
    finally:
        scheduler.shutdown(wait=False)
    assert "catch-up" in ids


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    def add_job(self, func: object, trigger: object, **kwargs: object) -> None:
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})

    def get_job(self, job_id: str) -> None:
        return None


def _item() -> BookingItem:
    return BookingItem(date(2026, 11, 16), 2, 68)


def _report(**kwargs: Any) -> RunReport:
    return RunReport(started_at=datetime(2026, 11, 13, 0, 5), dates=[date(2026, 11, 16)], **kwargs)


def _service(tmp_path, monkeypatch, outcome) -> tuple[DaemonService, FakeScheduler, list[int]]:
    settings = _settings(tmp_path)
    service = DaemonService(settings, StateStore(settings.webetu_state_path))
    scheduler = FakeScheduler()
    service.scheduler = scheduler  # type: ignore[assignment]
    calls: list[int] = []

    def fake_run(*_a: object, **_k: object) -> RunReport:
        calls.append(1)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr("webetu_resto.scheduler.run_with_prefs", fake_run)
    return service, scheduler, calls


async def test_build_scheduler_adds_auto_check_interval(tmp_path) -> None:
    settings = _settings(tmp_path, webetu_check_interval_minutes=30)
    scheduler = build_scheduler(settings, StateStore(settings.webetu_state_path), _job)
    scheduler.start(paused=True)
    try:
        ids = {job.id for job in scheduler.get_jobs()}
    finally:
        scheduler.shutdown(wait=False)
    assert "auto-check" in ids


async def test_build_scheduler_without_auto_check_when_disabled(tmp_path) -> None:
    settings = _settings(tmp_path, webetu_check_interval_minutes=0)
    scheduler = build_scheduler(settings, StateStore(settings.webetu_state_path), _job)
    scheduler.start(paused=True)
    try:
        ids = {job.id for job in scheduler.get_jobs()}
    finally:
        scheduler.shutdown(wait=False)
    assert "auto-check" not in ids


async def test_service_skips_when_auto_is_off(tmp_path, monkeypatch) -> None:
    service, scheduler, calls = _service(tmp_path, monkeypatch, _report())
    service.store.save(State(prefs=Prefs(auto=False)))
    await service.run()
    assert calls == []
    assert scheduler.jobs == []


async def test_service_quiet_when_everything_already_reserved(
    tmp_path, monkeypatch, capsys
) -> None:
    service, scheduler, _ = _service(tmp_path, monkeypatch, _report(skipped=[_item()]))
    await service.run()
    assert capsys.readouterr().out == ""
    assert scheduler.jobs == []


async def test_service_prints_report_when_something_booked(tmp_path, monkeypatch, capsys) -> None:
    service, scheduler, _ = _service(tmp_path, monkeypatch, _report(booked=[_item()]))
    await service.run()
    assert capsys.readouterr().out.strip() != ""
    assert scheduler.jobs == []


async def test_service_schedules_retry_on_api_error(tmp_path, monkeypatch) -> None:
    service, scheduler, _ = _service(tmp_path, monkeypatch, WebetuError("réseau indisponible"))
    await service.run()
    assert len(scheduler.jobs) == 1
    assert scheduler.jobs[0]["id"].startswith("retry-")


async def test_service_schedules_retry_on_partial_failure(tmp_path, monkeypatch) -> None:
    report = _report(failed=[(_item(), "complet")])
    service, scheduler, _ = _service(tmp_path, monkeypatch, report)
    await service.run()
    assert len(scheduler.jobs) == 1


async def test_retry_budget_is_capped(tmp_path, monkeypatch) -> None:
    service, scheduler, _ = _service(tmp_path, monkeypatch, WebetuError("down"))
    for _ in range(5):
        await service.run()
    assert len(scheduler.jobs) == 2  # webetu_max_retries == 2


async def test_default_settings_run_once_a_day_only(tmp_path) -> None:
    assert Settings(_env_file=None).webetu_check_interval_minutes == 0


async def test_service_logs_the_next_planned_run(tmp_path, monkeypatch, caplog) -> None:
    service, _, _ = _service(tmp_path, monkeypatch, _report(skipped=[_item()]))
    service.next_run = lambda: datetime(2026, 11, 15, 0, 5)  # type: ignore[method-assign]
    with caplog.at_level("INFO", logger="webetu_resto.scheduler"):
        await service.run()
    assert "prochain passage" in caplog.text
    assert "2026-11-15 00:05" in caplog.text
