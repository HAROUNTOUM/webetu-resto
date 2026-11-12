"""Pure scheduling helpers (no APScheduler import, easy to test)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from .errors import ConfigError

_RUN_AT_RE = re.compile(r"^(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)$")


def parse_run_at(value: str) -> tuple[int, int]:
    match = _RUN_AT_RE.match(value.strip())
    if not match:
        raise ConfigError(f"heure d'exécution invalide: {value!r} (format HH:MM)")
    return int(match.group("hour")), int(match.group("minute"))


def next_run_at(now: datetime, run_at: str) -> datetime:
    """Next occurrence of HH:MM in the same timezone as ``now``."""
    hour, minute = parse_run_at(run_at)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def needs_catch_up(last_run_day: str | None, today: date) -> bool:
    """True when the daily run did not happen yet for ``today``."""
    return last_run_day != today.isoformat()


def retry_delay_seconds(attempt: int, base: int = 20) -> int:
    """Exponential retry delay: base, 2*base, 4*base... (capped at 1 hour)."""
    delay = base * int(2 ** max(0, attempt))
    return min(delay, 3600)
