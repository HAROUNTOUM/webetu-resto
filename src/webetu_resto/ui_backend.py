"""The real backend of the local web interface (talks to Webetu, config, daemon)."""

from __future__ import annotations

import http.client
import json
import logging
import sys
import threading
import time
import webbrowser
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from . import autostart
from .background import BackgroundDaemon
from .booking import resolve_depot, target_dates
from .config import Settings
from .errors import ConfigError, WebetuError
from .onboarding import clear_config, save_config, verify_and_resolve
from .paths import resolve_env_file
from .runner import fetch_snapshot, options_from_settings, run_with_prefs
from .state import StateStore, effective_meals, effective_resto_id
from .ui import APP_ID, DEFAULT_PORT, UiError, UiServer, translate_error
from .update import current_version, fetch_latest, is_newer

logger = logging.getLogger(__name__)

PENDING_SECONDS = 15 * 60


@dataclass(slots=True)
class _Pending:
    """A verified login waiting for the restaurant choice. Memory only."""

    username: str
    password: str
    depot_ids: set[int]
    created: float


def _load_settings() -> Settings:
    try:
        return Settings()
    except (ValidationError, ConfigError) as exc:
        raise UiError("config", "invalid configuration file", 500) from exc


def _is_configured(settings: Settings) -> bool:
    return bool(settings.webetu_username.strip() and settings.password)


class LiveBackend:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: _Pending | None = None
        self._daemon = BackgroundDaemon()
        self._busy = False
        self._manual: dict[str, Any] | None = None
        self._update: dict[str, str] | None = None

    # ----------------------------------------------------------- lifecycle

    def start(self) -> None:
        settings: Settings | None
        try:
            settings = Settings()
        except (ValidationError, ConfigError):
            settings = None
        if settings is not None and _is_configured(settings):
            self._daemon.start(settings, StateStore(settings.webetu_state_path))
        if autostart.supported():
            autostart.refresh()
        threading.Thread(target=self._check_update, daemon=True).start()

    def close(self) -> None:
        self._daemon.stop()

    def _restart_daemon(self) -> None:
        self._daemon.stop()
        settings = _load_settings()
        if _is_configured(settings):
            self._daemon.start(settings, StateStore(settings.webetu_state_path))

    def _check_update(self) -> None:
        from . import _build

        if not _build.REPO:
            return
        latest = fetch_latest(_build.REPO)
        if latest is not None and is_newer(latest["version"], current_version()):
            self._update = latest

    # --------------------------------------------------------------- state

    def state(self) -> dict[str, Any]:
        settings = _load_settings()
        stored = StateStore(settings.webetu_state_path).load()
        configured = _is_configured(settings)
        last = stored.last_run
        days_since: int | None = None
        if last is not None:
            today = datetime.now(settings.timezone).date()
            try:
                days_since = (today - date.fromisoformat(last.day)).days
            except ValueError:
                days_since = None
        can_autostart = autostart.supported()
        return {
            "version": current_version(),
            "configured": configured,
            "username": settings.webetu_username if configured else "",
            "resto_id": effective_resto_id(settings.webetu_resto_id, stored),
            "auto": stored.prefs.auto,
            "daemon_running": self._daemon.running,
            "run_at": settings.webetu_run_at,
            "busy": self._busy,
            "manual": self._manual,
            "last_run": asdict(last) if last is not None else None,
            "days_since_last_run": days_since,
            "autostart": {
                "supported": can_autostart,
                "enabled": autostart.is_enabled() if can_autostart else False,
            },
            "update": self._update,
            "platform": sys.platform,
        }

    def status(self) -> dict[str, Any]:
        settings = _load_settings()
        if not _is_configured(settings):
            raise UiError("not_configured", "no account saved yet", 409)
        stored = StateStore(settings.webetu_state_path).load()
        options = options_from_settings(
            settings, resto_id=effective_resto_id(settings.webetu_resto_id, stored)
        )
        try:
            snapshot = fetch_snapshot(options)
        except WebetuError as exc:
            raise translate_error(exc) from exc
        meals = effective_meals(settings.meals, stored)
        booked = {(item.day, item.meal_type) for item in snapshot.reservations if item.meal_type}
        days = target_dates(datetime.now(settings.timezone).date(), settings.book_days)
        rows: list[dict[str, Any]] = []
        for day in days:
            cells: list[dict[str, Any]] = []
            for meal in meals:
                if not snapshot.depot.serves(meal):
                    cell_state = "not_served"
                elif (day, meal) in booked:
                    cell_state = "booked"
                else:
                    cell_state = "missing"
                cells.append({"type": meal, "state": cell_state})
            rows.append({"date": day.isoformat(), "weekday": day.weekday(), "meals": cells})
        return {
            "resto": snapshot.depot.display_name,
            "residence": snapshot.context.residence_name,
            "year": snapshot.context.year_code,
            "days": rows,
            "refreshed_at": datetime.now(settings.timezone).isoformat(timespec="seconds"),
        }

    # -------------------------------------------------------------- set-up

    def verify(self, username: str, password: str) -> dict[str, Any]:
        if not username or not password:
            raise UiError("bad_request", "matricule and password are required")
        settings = _load_settings()
        try:
            verified = verify_and_resolve(username, password, settings)
        except WebetuError as exc:
            raise translate_error(exc) from exc
        if not verified.depots:
            raise UiError("no_depots", "no restaurant returned by the server", 422)
        try:
            suggested: int | None = resolve_depot(verified.depots, None).id
        except ConfigError:
            suggested = None
        with self._lock:
            self._pending = _Pending(
                username=username,
                password=password,
                depot_ids={depot.id for depot in verified.depots},
                created=time.monotonic(),
            )
        ordered = sorted(verified.depots, key=lambda depot: (not depot.is_ru, depot.id))
        return {
            "residence": verified.context.residence_name,
            "year": verified.context.year_code,
            "suggested_id": suggested,
            "depots": [
                {
                    "id": depot.id,
                    "name": depot.display_name,
                    "is_ru": depot.is_ru,
                    "meals": [depot.breakfast, depot.lunch, depot.dinner],
                }
                for depot in ordered
            ],
        }

    def save(self, resto_id: int) -> dict[str, Any]:
        with self._lock:
            pending = self._pending
        if pending is None or time.monotonic() - pending.created > PENDING_SECONDS:
            raise UiError("expired", "verification expired, enter the password again", 409)
        if resto_id not in pending.depot_ids:
            raise UiError("bad_request", "unknown restaurant")
        settings = _load_settings()
        save_config(resolve_env_file(), pending.username, pending.password, resto_id)
        StateStore(settings.webetu_state_path).update_prefs(resto_id=resto_id, auto=True)
        with self._lock:
            self._pending = None
        self._restart_daemon()
        return self.state()

    # ------------------------------------------------------------- actions

    def run_now(self) -> dict[str, Any]:
        settings = _load_settings()
        if not _is_configured(settings):
            raise UiError("not_configured", "no account saved yet", 409)
        with self._lock:
            if self._busy:
                raise UiError("busy", "a booking pass is already running", 409)
            self._busy = True
        threading.Thread(target=self._run_worker, args=(settings,), daemon=True).start()
        return {"started": True}

    def _run_worker(self, settings: Settings) -> None:
        result: dict[str, Any] = {
            "at": datetime.now(settings.timezone).isoformat(timespec="seconds"),
            "ok": False,
            "booked": 0,
            "failed": 0,
            "skipped": 0,
            "error": None,
            "message": None,
        }
        try:
            report = run_with_prefs(settings, StateStore(settings.webetu_state_path))
            result.update(
                ok=report.ok,
                booked=len(report.booked),
                failed=len(report.failed),
                skipped=len(report.skipped),
            )
        except WebetuError as exc:
            error = translate_error(exc)
            result.update(error=error.code, message=error.message)
        except Exception as exc:
            logger.error("manual run crashed: %s", type(exc).__name__)
            result.update(error="unknown", message=type(exc).__name__)
        finally:
            with self._lock:
                self._manual = result
                self._busy = False

    def set_auto(self, enabled: bool) -> dict[str, Any]:
        settings = _load_settings()
        StateStore(settings.webetu_state_path).update_prefs(auto=enabled)
        return self.state()

    def set_autostart(self, enabled: bool) -> dict[str, Any]:
        if not autostart.supported():
            raise UiError("unsupported", "automatic start is only available on Windows", 400)
        if enabled:
            autostart.enable()
        else:
            autostart.disable()
        return self.state()

    def forget(self) -> dict[str, Any]:
        self._daemon.stop()
        try:
            settings: Settings | None = Settings()
        except (ValidationError, ConfigError):
            settings = None
        clear_config(resolve_env_file())
        if settings is not None:
            StateStore(settings.webetu_state_path).clear()
        if autostart.supported():
            autostart.disable()
        with self._lock:
            self._pending = None
            self._manual = None
        return self.state()


def _ping(port: int) -> bool:
    """True when another copy of this program already serves on ``port``."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1.5)
    try:
        connection.request("GET", "/api/ping")
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        return isinstance(data, dict) and data.get("app") == APP_ID
    except (OSError, ValueError):
        return False
    finally:
        connection.close()


def run_ui(*, port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    """Start the interface, or just open it when a copy is already running."""
    if _ping(port):
        if open_browser:
            webbrowser.open(f"http://127.0.0.1:{port}/")
        return
    backend = LiveBackend()
    try:
        server = UiServer(backend, port=port)
    except OSError:
        server = UiServer(backend, port=0)
    backend.start()
    logger.info("interface disponible sur %s", server.url)
    if open_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        backend.close()
        server.server_close()
