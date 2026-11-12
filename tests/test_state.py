from __future__ import annotations

import json
import sys
from datetime import date, datetime

from webetu_resto.models import BookingItem, RunReport
from webetu_resto.state import (
    LastRun,
    Prefs,
    State,
    StateStore,
    effective_meals,
    effective_resto_id,
    last_run_label,
)


def test_load_missing_returns_defaults(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json")
    assert store.load() == State()


def test_save_roundtrip_and_permissions(tmp_path) -> None:
    path = tmp_path / "state.json"
    store = StateStore(path)
    state = State(prefs=Prefs(meals=[1, 3], resto_id=68, auto=False), chat_id=42)
    store.save(state)
    assert store.load() == state
    if sys.platform != "win32":  # POSIX permission bits do not exist on Windows
        assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text())["prefs"]["meals"] == [1, 3]


def test_load_tolerates_broken_json(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json")
    assert StateStore(path).load() == State()


def test_load_tolerates_wrong_shapes(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 1, "prefs": "bad", "last_run": 3, "chat_id": "x"}))
    state = StateStore(path).load()
    assert state.prefs == Prefs()
    assert state.last_run is None
    assert state.chat_id is None


def test_load_tolerates_invalid_prefs(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"prefs": {"meals": [1, 9], "resto_id": "abc", "auto": 0}}))
    state = StateStore(path).load()
    assert state.prefs.meals is None
    assert state.prefs.resto_id is None
    assert state.prefs.auto is False


def test_load_incomplete_last_run_is_tolerated(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"last_run": {"day": "2026-11-12"}}))
    last_run = StateStore(path).load().last_run
    assert last_run is not None
    assert last_run.day == "2026-11-12"
    assert last_run.status == "unknown"
    assert last_run.at == ""


def test_update_prefs_and_clear(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.update_prefs(meals=[1, 2], resto_id=68, auto=False)
    state = store.load()
    assert state.prefs.meals == [1, 2]
    assert state.prefs.resto_id == 68
    assert state.prefs.auto is False
    store.clear()
    assert store.load() == State()


def test_record_run(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json")
    item = BookingItem(date(2026, 11, 13), 1, 68)
    report = RunReport(
        started_at=datetime(2026, 11, 12, 0, 5),
        dates=[item.day],
        booked=[item],
        skipped=[item],
        failed=[(item, "boom")],
    )
    state = store.record_run(report)
    assert state.last_run == LastRun(
        day="2026-11-12",
        status="partial",
        booked=1,
        skipped=1,
        failed=1,
        at="2026-11-12T00:05:00",
    )
    assert store.load().last_run == state.last_run


def test_set_chat_id(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.set_chat_id(99)
    assert store.load().chat_id == 99


def test_effective_helpers() -> None:
    state = State(prefs=Prefs(meals=[2], resto_id=479))
    assert effective_meals([1, 2, 3], state) == [2]
    assert effective_resto_id(68, state) == 479
    assert effective_meals([1], State()) == [1]
    assert effective_resto_id(68, State()) == 68


def test_last_run_label() -> None:
    assert last_run_label(State()) == "jamais"
    state = State(last_run=LastRun("2026-11-12", "ok", 3, 0, 0, "2026-11-12T00:05:00"))
    assert last_run_label(state) == "12/11 00:05"
    broken = State(last_run=LastRun("2026-11-12", "ok", 3, 0, 0, "nope"))
    assert last_run_label(broken) == "nope"
