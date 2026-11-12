from __future__ import annotations

from datetime import date, datetime

from webetu_resto.formatting import (
    format_cancellable,
    format_day,
    format_depots,
    format_last_run,
    format_report,
    format_settings,
    format_snapshot,
)
from webetu_resto.models import BookingItem, Depot, Reservation, RunReport, StudentContext
from webetu_resto.runner import Snapshot
from webetu_resto.state import LastRun, Prefs, State


def _report(**kwargs: object) -> RunReport:
    defaults: dict[str, object] = {
        "started_at": datetime(2026, 11, 12, 0, 5),
        "dates": [date(2026, 11, 13)],
    }
    defaults.update(kwargs)
    return RunReport(**defaults)  # type: ignore[arg-type]


def test_format_day_french() -> None:
    assert format_day(date(2026, 11, 14)) == "samedi 14 nov."
    assert format_day(date(2026, 1, 1)) == "jeudi 1 janv."


def test_format_report_empty() -> None:
    assert format_report(_report()).startswith("✅ Rien à réserver")


def test_format_report_dry_run(depot: Depot) -> None:
    item = BookingItem(date(2026, 11, 13), 1, depot.id)
    text = format_report(_report(depot=depot, planned=[item], dry_run=True))
    assert "Simulation" in text
    assert "RU EXAMPLE 02" in text
    assert "À réserver (1)" in text
    assert "Petit-déjeuner" in text


def test_format_report_booked_and_skipped(depot: Depot) -> None:
    item = BookingItem(date(2026, 11, 13), 2, depot.id)
    text = format_report(_report(depot=depot, booked=[item], skipped=[item]))
    assert "Réservation confirmée" in text
    assert "Réservés (1)" in text
    assert "Déjà réservés : 1" in text


def test_format_report_partial_and_warnings(depot: Depot) -> None:
    item = BookingItem(date(2026, 11, 13), 3, depot.id)
    text = format_report(
        _report(depot=depot, booked=[item], failed=[(item, "24h rule")], warnings=["attention"])
    )
    assert "partielle" in text
    assert "Échecs (1)" in text
    assert "24h rule" in text
    assert "⚠️ attention" in text


def test_format_report_failed_only(depot: Depot) -> None:
    item = BookingItem(date(2026, 11, 13), 1, depot.id)
    text = format_report(_report(depot=depot, failed=[(item, "boom")]))
    assert "impossible" in text


def test_format_snapshot(depot: Depot) -> None:
    context = StudentContext(
        username="123456789",
        token="secret",
        uuid="uuid",
        id_individu=1,
        id_etablissement=2,
        residence_name="Résidence",
    )
    reservation = Reservation(
        1, date(2026, 11, 13), 2, "Déjeuner", "غداء", depot.display_name, True
    )
    snapshot = Snapshot(context, depot, [depot], [reservation])
    text = format_snapshot(snapshot, [date(2026, 11, 13)], [1, 2, 3])
    assert "123456789" in text
    assert "Résidence" in text
    assert "✅ Déj" in text
    assert "⬜ Petit-déj" in text
    assert "⬜ Dîner" in text


def test_format_settings(settings) -> None:
    state = State(prefs=Prefs(meals=[1, 3], auto=False))
    text = format_settings(settings, state, "68 - RU EXAMPLE 02")
    assert "RU EXAMPLE 02" in text
    assert "Petit-déjeuner, Dîner" in text
    assert "Automatique : non" in text


def test_format_settings_without_label(settings) -> None:
    text = format_settings(settings, State())
    assert "68" in text
    assert "Automatique : oui" in text


def test_format_cancellable() -> None:
    today = date(2026, 11, 12)
    rows = [
        Reservation(1, today, 1, "Petit-déjeuner", "فطور", "RU", True),
        Reservation(2, today, 2, "Déjeuner", "غداء", "RU", False),
        Reservation(3, date(2026, 11, 11), 3, "Dîner", "عشاء", "RU", True),
    ]
    text = format_cancellable(rows, today)
    assert "1 — jeudi 12 nov." in text
    assert "2 —" not in text
    assert "3 —" not in text
    assert "Aucune" in format_cancellable([], today)


def test_format_depots(depots: list[Depot]) -> None:
    text = format_depots(depots)
    assert "1. 57 - RU 57 (RU)" in text
    assert "2. 68 - RU EXAMPLE 02 (RU)" in text
    assert "3. 479 - RU 479" in text


def test_format_last_run() -> None:
    assert format_last_run(State()) == "Dernier passage : jamais"
    state = State(last_run=LastRun("2026-11-12", "ok", 3, 1, 0, "2026-11-12T00:05:00"))
    assert "3 réservés" in format_last_run(state)
