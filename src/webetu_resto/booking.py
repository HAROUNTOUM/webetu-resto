"""Pure booking logic: what to book, what to skip, how to read the answer."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from .errors import ConfigError
from .meals import meal_label
from .models import BookingItem, BookingResult, Depot, Reservation


@dataclass(slots=True)
class Plan:
    items: list[BookingItem] = field(default_factory=list)
    skipped: list[BookingItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def target_dates(today: date, offsets: Iterable[int]) -> list[date]:
    """Return the sorted target days for the rolling window."""
    return sorted({today + timedelta(days=offset) for offset in offsets})


def resolve_depot(depots: Sequence[Depot], wanted_id: int | None) -> Depot:
    """Pick the configured restaurant, or auto-detect when unambiguous."""
    if wanted_id is not None:
        for depot in depots:
            if depot.id == wanted_id:
                return depot
        available = ", ".join(depot.label for depot in depots) or "aucun"
        raise ConfigError(f"restaurant {wanted_id} introuvable. Disponibles : {available}")

    restaurants = [depot for depot in depots if depot.is_ru]
    if len(restaurants) == 1:
        return restaurants[0]
    if not restaurants:
        raise ConfigError(
            "aucun restaurant universitaire (isRu=1) trouvé ; définis WEBETU_RESTO_ID"
        )
    labels = ", ".join(depot.label for depot in restaurants)
    raise ConfigError(f"plusieurs restaurants possibles ({labels}) ; définis WEBETU_RESTO_ID")


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.strip().casefold())
    without_accents = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(without_accents.split())


def _same_depot(left: str, right: str) -> bool:
    if not left or not right:
        return True
    return _normalize(left) == _normalize(right)


def plan_reservations(
    existing: Sequence[Reservation],
    days: Sequence[date],
    meals: Sequence[int],
    depot: Depot,
    *,
    today: date | None = None,
) -> Plan:
    """Diff the rolling window against existing reservations (idempotent)."""
    plan = Plan()
    booked_slots: dict[tuple[date, int], Reservation] = {}
    unknown_labels: set[str] = set()

    for reservation in existing:
        if reservation.meal_type is None:
            if reservation.label_fr or reservation.label_ar:
                unknown_labels.add(reservation.label_fr or reservation.label_ar)
            continue
        booked_slots[(reservation.day, reservation.meal_type)] = reservation

    for label in sorted(unknown_labels):
        plan.warnings.append(f"repas au libellé inconnu ignoré : {label}")

    for day in sorted(days):
        if today is not None and day < today:
            continue
        for meal in sorted(meals):
            item = BookingItem(day=day, meal_type=meal, depot_id=depot.id)

            if not depot.serves(meal):
                plan.warnings.append(
                    f"{meal_label(meal)} n'est pas servi à {depot.display_name} ({day.isoformat()})"
                )
                continue

            existing_reservation = booked_slots.get((day, meal))
            if existing_reservation is None:
                plan.items.append(item)
                continue

            plan.skipped.append(item)
            if not _same_depot(existing_reservation.depot_fr, depot.display_name):
                plan.warnings.append(
                    f"{meal_label(meal)} du {day.isoformat()} déjà réservé à "
                    f"{existing_reservation.depot_fr or 'un autre restaurant'}"
                )

    return plan


def apply_results(
    items: Sequence[BookingItem], results: Sequence[BookingResult]
) -> tuple[list[BookingItem], list[tuple[BookingItem, str]]]:
    """Map the API's per-item answer back to the requested items."""
    by_slot = {
        (result.day, result.meal_type): result
        for result in results
        if result.day is not None and result.meal_type is not None
    }
    booked: list[BookingItem] = []
    failed: list[tuple[BookingItem, str]] = []
    for index, item in enumerate(items):
        result = by_slot.get((item.day, item.meal_type))
        if result is None and len(results) == len(items):
            result = results[index]
        if result is None:
            failed.append((item, "réponse manquante du serveur"))
        elif result.success:
            booked.append(item)
        else:
            failed.append((item, result.message or "refusé par le serveur"))
    return booked, failed
