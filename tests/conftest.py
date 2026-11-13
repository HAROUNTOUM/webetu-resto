"""Shared fixtures. Every Settings instance must ignore the real .env file."""

from __future__ import annotations

import os
from datetime import date

import pytest

from webetu_resto.config import Settings
from webetu_resto.models import Depot, Reservation


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path_factory) -> None:
    for key in list(os.environ):
        if key.startswith(("WEBETU_", "TELEGRAM_")):
            monkeypatch.delenv(key, raising=False)
    # Never touch the developer's real config directory from a test.
    monkeypatch.setenv("WEBETU_CONFIG_DIR", str(tmp_path_factory.mktemp("config")))


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        webetu_username="123456789",
        webetu_password="test-password",
        webetu_resto_id=68,
        webetu_request_interval=0,
        webetu_state_path="data/test-state.json",
    )


@pytest.fixture
def depot() -> Depot:
    return Depot(
        id=68,
        name_fr="RU EXAMPLE 02",
        name_ar="",
        is_ru=True,
        breakfast=True,
        lunch=True,
        dinner=True,
    )


@pytest.fixture
def depots(depot: Depot) -> list[Depot]:
    return [
        Depot(57, "RU 57", "", True, True, True, True),
        depot,
        Depot(479, "RU 479", "", False, True, True, True),
    ]


@pytest.fixture
def existing() -> list[Reservation]:
    return [
        Reservation(
            id=65100001,
            day=date(2026, 11, 12),
            meal_type=1,
            label_fr="Petit-déjeuner",
            label_ar="فطور",
            depot_fr="RU EXAMPLE 02",
            candelete=False,
        ),
        Reservation(
            id=65100002,
            day=date(2026, 11, 13),
            meal_type=2,
            label_fr="Déjeuner",
            label_ar="غداء",
            depot_fr="RU EXAMPLE 02",
            candelete=True,
        ),
    ]
