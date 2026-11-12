"""Configuration loaded from environment variables / .env."""

from __future__ import annotations

import re
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigError
from .meals import parse_meals
from .signing import DEFAULT_HMAC_SECRET

_RUN_AT_RE = re.compile(r"^(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)$")


def parse_days(value: str) -> list[int]:
    """Parse the rolling window (allowed offsets: 1, 2 or 3 days)."""
    try:
        parts = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise ConfigError(f"WEBETU_BOOK_DAYS is invalid: {value!r}") from exc
    days = sorted(set(parts))
    if not days:
        raise ConfigError("WEBETU_BOOK_DAYS must contain at least one day")
    invalid = [day for day in days if day not in (1, 2, 3)]
    if invalid:
        raise ConfigError(f"WEBETU_BOOK_DAYS only accepts 1, 2 or 3 (got {invalid})")
    return days


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Credentials ---------------------------------------------------------
    webetu_username: str = ""
    webetu_password: SecretStr = SecretStr("")
    webetu_resto_id: int | None = None

    # Endpoints (overridable for tests / future API moves) ----------------
    webetu_progres_base: str = "https://api-webetu.mesrs.dz"
    webetu_resto_base: str = "https://gs-api.onou.dz"
    webetu_hmac_secret: SecretStr = SecretStr(DEFAULT_HMAC_SECRET)

    # Scheduling ----------------------------------------------------------
    webetu_timezone: str = "Africa/Algiers"
    webetu_run_at: str = "00:05"
    webetu_book_days: str = "1,2,3"
    webetu_meals: str = "1,2,3"

    # Runtime -------------------------------------------------------------
    webetu_state_path: Path = Path("data/state.json")
    webetu_dry_run: bool = False
    webetu_max_retries: int = 2
    webetu_retry_delay: int = 20
    webetu_request_interval: float = 0.3
    webetu_log_level: str = "INFO"

    @field_validator("webetu_run_at")
    @classmethod
    def _validate_run_at(cls, value: str) -> str:
        if not _RUN_AT_RE.match(value.strip()):
            raise ValueError("WEBETU_RUN_AT must look like HH:MM (00:00 to 23:59)")
        return value.strip()

    @field_validator("webetu_log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"invalid log level: {value!r}")
        return level

    @model_validator(mode="after")
    def _validate_lists(self) -> Settings:
        # Accessing the properties validates both list formats eagerly.
        _ = (self.book_days, self.meals)
        return self

    @property
    def book_days(self) -> list[int]:
        return parse_days(self.webetu_book_days)

    @property
    def meals(self) -> list[int]:
        try:
            return parse_meals(self.webetu_meals)
        except ValueError as exc:
            raise ConfigError(f"WEBETU_MEALS is invalid: {exc}") from exc

    @property
    def timezone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.webetu_timezone)
        except Exception as exc:  # ZoneInfoNotFoundError, ValueError
            raise ConfigError(f"unknown timezone: {self.webetu_timezone!r}") from exc

    @property
    def run_at_parts(self) -> tuple[int, int]:
        match = _RUN_AT_RE.match(self.webetu_run_at)
        if not match:
            raise ConfigError(f"invalid WEBETU_RUN_AT: {self.webetu_run_at!r}")
        return int(match.group("hour")), int(match.group("minute"))

    @property
    def hmac_secret(self) -> str:
        return self.webetu_hmac_secret.get_secret_value()

    @property
    def password(self) -> str:
        return self.webetu_password.get_secret_value()

    def require_credentials(self) -> None:
        if not self.webetu_username.strip() or not self.password:
            raise ConfigError(
                "WEBETU_USERNAME and WEBETU_PASSWORD are required. Run `webtu setup`."
            )

    def describe(self) -> dict[str, object]:
        """Safe diagnostics: never contains credentials or tokens."""
        return {
            "resto_id": self.webetu_resto_id,
            "timezone": self.webetu_timezone,
            "run_at": self.webetu_run_at,
            "book_days": self.book_days,
            "meals": self.meals,
            "state_path": str(self.webetu_state_path),
            "dry_run": self.webetu_dry_run,
        }
