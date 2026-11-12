"""French, phone-friendly text rendering for the CLI and the Telegram bot."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any

from .meals import meal_label
from .models import BookingItem, Depot, Reservation, RunReport
from .runner import Snapshot
from .state import State

WEEKDAYS_FR = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)
MONTHS_FR = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)
SHORT_MEALS_FR = {1: "Petit-déj", 2: "Déj", 3: "Dîner"}


def format_day(day: date) -> str:
    return f"{WEEKDAYS_FR[day.weekday()]} {day.day} {MONTHS_FR[day.month - 1]}"


def _group(items: Iterable[BookingItem]) -> dict[date, list[str]]:
    grouped: dict[date, list[str]] = defaultdict(list)
    for item in items:
        grouped[item.day].append(item.label)
    return dict(grouped)


def format_report(report: RunReport) -> str:
    if report.dry_run:
        header = "🧪 Simulation — rien n'a été envoyé"
    elif report.failed and report.booked:
        header = "⚠️ Réservation partielle"
    elif report.failed:
        header = "❌ Réservation impossible"
    elif report.booked:
        header = "✅ Réservation confirmée"
    else:
        header = "✅ Rien à réserver"

    lines = [header]
    if report.depot is not None:
        lines.append(f"📍 {report.depot.label}")
    if report.dates:
        lines.append("🗓 " + " · ".join(format_day(day) for day in report.dates))

    if report.dry_run and report.planned:
        lines.append("")
        lines.append(f"🧾 À réserver ({len(report.planned)})")
        for day, labels in sorted(_group(report.planned).items()):
            lines.append(f"  • {format_day(day)} : {', '.join(labels)}")
    elif report.booked:
        lines.append("")
        lines.append(f"✅ Réservés ({len(report.booked)})")
        for day, labels in sorted(_group(report.booked).items()):
            lines.append(f"  • {format_day(day)} : {', '.join(labels)}")

    if report.skipped:
        lines.append(f"♻️ Déjà réservés : {len(report.skipped)} repas")

    if report.failed:
        lines.append("")
        lines.append(f"❌ Échecs ({len(report.failed)})")
        for item, message in report.failed:
            lines.append(f"  • {format_day(item.day)} : {item.label} — {message}")

    if report.warnings:
        lines.append("")
        for warning in report.warnings:
            lines.append(f"⚠️ {warning}")

    return "\n".join(lines)


def format_snapshot(snapshot: Snapshot, days: Sequence[date], meals: Sequence[int]) -> str:
    context = snapshot.context
    lines = [
        f"👤 {context.username}",
    ]
    if context.residence_name:
        lines.append(f"🏠 {context.residence_name}")
    lines.append(f"🍽 {snapshot.depot.label}")

    booked = {
        (reservation.day, reservation.meal_type)
        for reservation in snapshot.reservations
        if reservation.meal_type is not None
    }
    lines.append("")
    for day in days:
        cells = []
        for meal in meals:
            marker = "✅" if (day, meal) in booked else "⬜"
            cells.append(f"{marker} {SHORT_MEALS_FR.get(meal, meal_label(meal))}")
        lines.append(f"{format_day(day)} : {' · '.join(cells)}")
    return "\n".join(lines)


def format_settings(settings: Any, state: State, depot_label: str | None = None) -> str:
    from .state import effective_meals, effective_resto_id

    meals = effective_meals(settings.meals, state)
    resto_id = effective_resto_id(settings.webetu_resto_id, state)
    restaurant = depot_label or (str(resto_id) if resto_id else "auto")
    auto = "oui" if state.prefs.auto else "non"
    return "\n".join(
        [
            "⚙️ Réglages",
            f"🍽 Restaurant : {restaurant}",
            f"🍴 Repas : {', '.join(meal_label(meal) for meal in meals)}",
            f"🤖 Automatique : {auto}",
            f"⏰ Passage quotidien : {settings.webetu_run_at} ({settings.webetu_timezone})",
        ]
    )


def format_cancellable(reservations: Sequence[Reservation], today: date) -> str:
    rows = [
        reservation
        for reservation in reservations
        if reservation.candelete and reservation.day >= today and reservation.meal_type is not None
    ]
    if not rows:
        return "Aucune réservation annulable pour le moment."
    lines = ["Réservations annulables :"]
    for reservation in rows:
        lines.append(
            f"  • {reservation.id} — {format_day(reservation.day)} — "
            f"{reservation.label} — {reservation.depot_fr}"
        )
    return "\n".join(lines)


def format_depots(depots: Sequence[Depot]) -> str:
    return "\n".join(
        f"{index}. {depot.label}{' (RU)' if depot.is_ru else ''}"
        for index, depot in enumerate(depots, start=1)
    )


def format_last_run(state: State) -> str:
    if state.last_run is None:
        return "Dernier passage : jamais"
    return (
        f"Dernier passage : {state.last_run.at} — {state.last_run.status} "
        f"({state.last_run.booked} réservés, {state.last_run.failed} échecs)"
    )
