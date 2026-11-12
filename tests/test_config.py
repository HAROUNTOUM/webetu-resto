from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from webetu_resto.config import Settings, parse_days
from webetu_resto.errors import ConfigError


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "webetu_username": "123456789",
        "webetu_password": "secret",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_defaults() -> None:
    settings = _settings()
    assert settings.book_days == [1, 2, 3]
    assert settings.meals == [1, 2, 3]
    assert settings.run_at_parts == (0, 5)
    assert settings.timezone.key == "Africa/Algiers"
    assert settings.password == "secret"
    assert settings.hmac_secret
    assert settings.describe()["resto_id"] is None


def test_env_variables_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBETU_USERNAME", "987654321")
    monkeypatch.setenv("WEBETU_PASSWORD", "from-env")
    monkeypatch.setenv("WEBETU_BOOK_DAYS", "2,3")
    monkeypatch.setenv("WEBETU_MEALS", "1")
    monkeypatch.setenv("WEBETU_RUN_AT", "23:59")
    settings = Settings(_env_file=None)
    assert settings.webetu_username == "987654321"
    assert settings.password == "from-env"
    assert settings.book_days == [2, 3]
    assert settings.meals == [1]
    assert settings.run_at_parts == (23, 59)


@pytest.mark.parametrize("value", ["", "24:00", "12:60", "midi", "1:2"])
def test_invalid_run_at(value: str) -> None:
    with pytest.raises(ValidationError):
        _settings(webetu_run_at=value)


@pytest.mark.parametrize("value", ["0", "4", "1,4", "", "a"])
def test_invalid_days(value: str) -> None:
    with pytest.raises(ConfigError):
        parse_days(value)


def test_invalid_days_through_settings() -> None:
    with pytest.raises(ConfigError):
        _settings(webetu_book_days="0,1")


def test_invalid_meals_through_settings() -> None:
    with pytest.raises(ConfigError):
        _settings(webetu_meals="1,9")


def test_invalid_log_level() -> None:
    with pytest.raises(ValidationError):
        _settings(webetu_log_level="LOUD")


def test_unknown_timezone() -> None:
    settings = _settings(webetu_timezone="Mars/Olympus")
    with pytest.raises(ConfigError):
        _ = settings.timezone


def test_require_credentials() -> None:
    with pytest.raises(ConfigError):
        _settings(webetu_username="", webetu_password="").require_credentials()
    _settings().require_credentials()


def test_describe_never_leaks_secrets() -> None:
    settings = _settings(
        webetu_resto_id=68,
    )
    payload = json.dumps(settings.describe(), ensure_ascii=False)
    assert "secret" not in payload
    assert "123456789" not in payload
    assert "password" not in payload
    assert "token" not in payload


def test_paths_and_booleans_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBETU_STATE_PATH", "/tmp/custom.json")
    monkeypatch.setenv("WEBETU_DRY_RUN", "true")
    monkeypatch.setenv("WEBETU_MAX_RETRIES", "5")
    settings = Settings(_env_file=None)
    assert settings.webetu_state_path == Path("/tmp/custom.json")
    assert settings.webetu_dry_run is True
    assert settings.webetu_max_retries == 5


def test_empty_env_values_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    # GitHub Actions passes unset secrets as empty strings.
    monkeypatch.setenv("WEBETU_RESTO_ID", "")
    monkeypatch.setenv("WEBETU_RUN_AT", "")
    settings = Settings(_env_file=None)
    assert settings.webetu_resto_id is None
    assert settings.webetu_run_at == "00:05"
