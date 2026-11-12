from __future__ import annotations

from datetime import date, datetime

from webetu_resto.models import BookingItem, BookingResult, Depot, Reservation, RunReport


def test_depot_serves_and_labels() -> None:
    depot = Depot(68, "RU EXAMPLE 02", "", True, True, False, True)
    assert depot.display_name == "RU EXAMPLE 02"
    assert depot.label == "68 - RU EXAMPLE 02"
    assert depot.serves(1)
    assert not depot.serves(2)
    assert not depot.serves(99)


def test_depot_falls_back_to_arabic_name() -> None:
    depot = Depot(57, "", "إقامة", False, True, True, True)
    assert depot.display_name == "إقامة"


def test_booking_item_payload_is_compact_and_ordered() -> None:
    item = BookingItem(date(2026, 11, 14), 1, 68)
    assert item.iso_day == "2026-11-14"
    assert item.payload() == {
        "date_reserve": "2026-11-14",
        "menu_type": 1,
        "idDepot": 68,
    }
    assert item.label == "Petit-déjeuner"


def test_reservation_label_uses_meal_type_then_french() -> None:
    known = Reservation(1, date(2026, 11, 14), 2, "Déjeuner", "غداء", "RU", True)
    unknown = Reservation(2, date(2026, 11, 14), None, "Brunch", "", "RU", True)
    assert known.label == "Déjeuner"
    assert unknown.label == "Brunch"


def test_run_report_status_and_total() -> None:
    item = BookingItem(date(2026, 11, 14), 1, 68)
    now = datetime(2026, 11, 12, 0, 5)
    empty = RunReport(started_at=now, dates=[item.day])
    assert empty.status == "ok"
    assert empty.ok
    assert empty.total == 0

    dry = RunReport(started_at=now, dates=[item.day], planned=[item], dry_run=True)
    assert dry.status == "dry-run"

    booked = RunReport(started_at=now, dates=[item.day], booked=[item])
    assert booked.status == "ok"
    assert booked.total == 1

    partial = RunReport(started_at=now, dates=[item.day], booked=[item], failed=[(item, "x")])
    assert partial.status == "partial"
    assert not partial.ok

    failed = RunReport(started_at=now, dates=[item.day], failed=[(item, "x")])
    assert failed.status == "failed"


def test_booking_result_is_frozen() -> None:
    result = BookingResult(date(2026, 11, 14), 1, True, "ok")
    assert result.success
