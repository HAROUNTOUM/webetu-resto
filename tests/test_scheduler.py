from __future__ import annotations

from datetime import datetime

import pytest

from webetu_resto.config import Settings
from webetu_resto.scheduler import build_scheduler
from webetu_resto.state import LastRun, State, StateStore


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
