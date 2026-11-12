from __future__ import annotations

from datetime import date

import pytest

from webetu_resto.booking import apply_results, plan_reservations, resolve_depot, target_dates
from webetu_resto.errors import ConfigError
from webetu_resto.models import BookingItem, BookingResult, Depot, Reservation


def test_target_dates_sorted_unique() -> None:
    today = date(2026, 11, 12)
    assert target_dates(today, [3, 1, 2, 1]) == [
        date(2026, 11, 13),
        date(2026, 11, 14),
        date(2026, 11, 15),
    ]


def test_resolve_depot_explicit(depots: list[Depot]) -> None:
    assert resolve_depot(depots, 479).id == 479


def test_resolve_depot_missing_explicit(depots: list[Depot]) -> None:
    with pytest.raises(ConfigError, match="introuvable"):
        resolve_depot(depots, 999)


def test_resolve_depot_auto_with_single_ru(depot: Depot) -> None:
    assert resolve_depot([depot], None).id == 68


def test_resolve_depot_auto_is_ambiguous() -> None:
    depots = [
        Depot(1, "A", "", True, True, True, True),
        Depot(2, "B", "", True, True, True, True),
    ]
    with pytest.raises(ConfigError, match="plusieurs"):
        resolve_depot(depots, None)


def test_resolve_depot_auto_without_ru() -> None:
    depots = [Depot(1, "A", "", False, True, True, True)]
    with pytest.raises(ConfigError, match="aucun restaurant"):
        resolve_depot(depots, None)


def test_plan_fresh_window(depot: Depot) -> None:
    plan = plan_reservations(
        [],
        [date(2026, 11, 13), date(2026, 11, 14)],
        [1, 2],
        depot,
        today=date(2026, 11, 12),
    )
    assert len(plan.items) == 4
    assert plan.skipped == []
    assert plan.warnings == []


def test_plan_skips_existing_same_depot(depot: Depot, existing: list[Reservation]) -> None:
    plan = plan_reservations(
        existing,
        [date(2026, 11, 12), date(2026, 11, 13), date(2026, 11, 14)],
        [1, 2, 3],
        depot,
        today=date(2026, 11, 12),
    )
    assert len(plan.items) == 7
    assert len(plan.skipped) == 2
    assert plan.warnings == []


def test_plan_warns_when_existing_is_elsewhere(depot: Depot) -> None:
    reservation = Reservation(1, date(2026, 11, 13), 2, "Déjeuner", "غداء", "AUTRE RU", True)
    plan = plan_reservations(
        [reservation],
        [date(2026, 11, 13)],
        [2],
        depot,
        today=date(2026, 11, 12),
    )
    assert plan.items == []
    assert len(plan.skipped) == 1
    assert "déjà réservé" in plan.warnings[0]


def test_plan_ignores_past_days(depot: Depot) -> None:
    plan = plan_reservations(
        [],
        [date(2026, 11, 11), date(2026, 11, 12)],
        [1],
        depot,
        today=date(2026, 11, 12),
    )
    assert [item.day for item in plan.items] == [date(2026, 11, 12)]


def test_plan_skips_meal_not_served() -> None:
    depot = Depot(1, "RU", "", True, True, False, True)
    plan = plan_reservations(
        [],
        [date(2026, 11, 13)],
        [1, 2, 3],
        depot,
        today=date(2026, 11, 12),
    )
    assert [item.meal_type for item in plan.items] == [1, 3]
    assert any("n'est pas servi" in warning for warning in plan.warnings)


def test_plan_warns_about_unknown_labels(depot: Depot) -> None:
    reservation = Reservation(1, date(2026, 11, 13), None, "Brunch", "", "RU", True)
    plan = plan_reservations(
        [reservation],
        [date(2026, 11, 13)],
        [1],
        depot,
        today=date(2026, 11, 12),
    )
    assert len(plan.items) == 1
    assert any("libellé inconnu" in warning for warning in plan.warnings)


def test_apply_results_matches_by_slot(depot: Depot) -> None:
    items = [
        BookingItem(date(2026, 11, 13), 1, depot.id),
        BookingItem(date(2026, 11, 13), 2, depot.id),
    ]
    results = [
        BookingResult(date(2026, 11, 13), 2, True, "ok"),
        BookingResult(date(2026, 11, 13), 1, True, "ok"),
    ]
    booked, failed = apply_results(items, results)
    assert booked == items
    assert failed == []


def test_apply_results_falls_back_to_position(depot: Depot) -> None:
    items = [
        BookingItem(date(2026, 11, 13), 1, depot.id),
        BookingItem(date(2026, 11, 13), 2, depot.id),
    ]
    results = [
        BookingResult(None, None, True, "ok"),
        BookingResult(None, None, False, ""),
    ]
    booked, failed = apply_results(items, results)
    assert booked == [items[0]]
    assert failed == [(items[1], "refusé par le serveur")]


def test_apply_results_reports_missing_answer(depot: Depot) -> None:
    items = [BookingItem(date(2026, 11, 13), 1, depot.id)]
    booked, failed = apply_results(items, [])
    assert booked == []
    assert failed == [(items[0], "réponse manquante du serveur")]
