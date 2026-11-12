from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from webetu_resto.errors import ConfigError
from webetu_resto.schedule import (
    needs_catch_up,
    next_run_at,
    parse_run_at,
    retry_delay_seconds,
)

TZ = ZoneInfo("Africa/Algiers")


def test_parse_run_at() -> None:
    assert parse_run_at("00:05") == (0, 5)
    assert parse_run_at(" 23:59 ") == (23, 59)
    with pytest.raises(ConfigError):
        parse_run_at("24:00")


def test_next_run_at_is_tomorrow_when_time_passed() -> None:
    now = datetime(2026, 11, 12, 8, 0, tzinfo=TZ)
    assert next_run_at(now, "00:05") == datetime(2026, 11, 13, 0, 5, tzinfo=TZ)


def test_next_run_at_is_today_when_still_ahead() -> None:
    now = datetime(2026, 11, 12, 0, 0, tzinfo=TZ)
    assert next_run_at(now, "00:05") == datetime(2026, 11, 12, 0, 5, tzinfo=TZ)


def test_needs_catch_up() -> None:
    today = date(2026, 11, 12)
    assert needs_catch_up(None, today)
    assert needs_catch_up("2026-11-11", today)
    assert not needs_catch_up("2026-11-12", today)


def test_retry_delay_grows_then_caps() -> None:
    assert retry_delay_seconds(0) == 20
    assert retry_delay_seconds(1) == 40
    assert retry_delay_seconds(2) == 80
    assert retry_delay_seconds(20) == 3600
