"""Persistent state: user preferences and the last run summary."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .meals import parse_meals
from .models import RunReport


@dataclass(slots=True)
class Prefs:
    """Runtime overrides set from the Telegram bot."""

    meals: list[int] | None = None
    resto_id: int | None = None
    auto: bool = True


@dataclass(slots=True)
class LastRun:
    day: str
    status: str
    booked: int
    skipped: int
    failed: int
    at: str


@dataclass(slots=True)
class State:
    version: int = 1
    prefs: Prefs = field(default_factory=Prefs)
    last_run: LastRun | None = None
    chat_id: int | None = None


def _load_prefs(raw: object) -> Prefs:
    if not isinstance(raw, dict):
        return Prefs()
    meals: list[int] | None = None
    if raw.get("meals") is not None:
        try:
            meals = parse_meals(raw["meals"])
        except (TypeError, ValueError):
            meals = None
    resto_id = raw.get("resto_id")
    try:
        resto_id = int(resto_id) if resto_id is not None else None
    except (TypeError, ValueError):
        resto_id = None
    return Prefs(meals=meals, resto_id=resto_id, auto=bool(raw.get("auto", True)))


def _load_last_run(raw: object) -> LastRun | None:
    if not isinstance(raw, dict):
        return None
    try:
        return LastRun(
            day=str(raw["day"]),
            status=str(raw.get("status") or "unknown"),
            booked=int(raw.get("booked") or 0),
            skipped=int(raw.get("skipped") or 0),
            failed=int(raw.get("failed") or 0),
            at=str(raw.get("at") or ""),
        )
    except (KeyError, TypeError, ValueError):
        return None


class StateStore:
    """Atomic JSON store. Small enough to be read on every request."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def load(self) -> State:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return State()
        if not isinstance(raw, dict):
            return State()
        chat_id = raw.get("chat_id")
        try:
            chat_id = int(chat_id) if chat_id is not None else None
        except (TypeError, ValueError):
            chat_id = None
        return State(
            version=int(raw.get("version") or 1),
            prefs=_load_prefs(raw.get("prefs")),
            last_run=_load_last_run(raw.get("last_run")),
            chat_id=chat_id,
        )

    def save(self, state: State) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + ".tmp")
            payload = json.dumps(asdict(state), ensure_ascii=False, indent=2)
            temporary.write_text(payload + "\n", encoding="utf-8")
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)

    def record_run(self, report: RunReport) -> State:
        state = self.load()
        state.last_run = LastRun(
            day=report.started_at.date().isoformat(),
            status=report.status,
            booked=len(report.booked),
            skipped=len(report.skipped),
            failed=len(report.failed),
            at=report.started_at.isoformat(timespec="seconds"),
        )
        self.save(state)
        return state

    def set_chat_id(self, chat_id: int) -> State:
        state = self.load()
        state.chat_id = chat_id
        self.save(state)
        return state

    def update_prefs(
        self,
        *,
        meals: list[int] | None = None,
        resto_id: int | None = None,
        auto: bool | None = None,
    ) -> State:
        state = self.load()
        if meals is not None:
            state.prefs.meals = parse_meals(meals)
        if resto_id is not None:
            state.prefs.resto_id = int(resto_id)
        if auto is not None:
            state.prefs.auto = bool(auto)
        self.save(state)
        return state

    def clear(self) -> None:
        with self._lock:
            self.path.unlink(missing_ok=True)
            temporary = self.path.with_name(self.path.name + ".tmp")
            temporary.unlink(missing_ok=True)


def effective_meals(default: list[int], state: State) -> list[int]:
    return state.prefs.meals or default


def effective_resto_id(default: int | None, state: State) -> int | None:
    return state.prefs.resto_id if state.prefs.resto_id is not None else default


def last_run_label(state: State, *, timezone: str = "Africa/Algiers") -> str:
    if state.last_run is None:
        return "jamais"
    try:
        moment = datetime.fromisoformat(state.last_run.at)
        return moment.strftime("%d/%m %H:%M")
    except ValueError:
        return state.last_run.at or "inconnu"
