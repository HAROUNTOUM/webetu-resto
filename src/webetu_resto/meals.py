"""Meal type identifiers and labels.

The Webetu API uses 1/2/3 for breakfast/lunch/dinner internally, but the
reservations listing only exposes French and Arabic labels. These mappings are
the fragile part of the integration: if ONOU changes the wording, update them.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

MEAL_BREAKFAST = 1
MEAL_LUNCH = 2
MEAL_DINNER = 3

MEAL_LABELS_FR: dict[int, str] = {
    MEAL_BREAKFAST: "Petit-déjeuner",
    MEAL_LUNCH: "Déjeuner",
    MEAL_DINNER: "Dîner",
}
MEAL_LABELS_AR: dict[int, str] = {
    MEAL_BREAKFAST: "فطور",
    MEAL_LUNCH: "غداء",
    MEAL_DINNER: "عشاء",
}
MEAL_LABELS_EN: dict[int, str] = {
    MEAL_BREAKFAST: "Breakfast",
    MEAL_LUNCH: "Lunch",
    MEAL_DINNER: "Dinner",
}

_LABELS = (MEAL_LABELS_FR, MEAL_LABELS_AR, MEAL_LABELS_EN)
ALL_MEALS = (MEAL_BREAKFAST, MEAL_LUNCH, MEAL_DINNER)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


_NORMALIZED: dict[str, int] = {}
for _mapping in _LABELS:
    for _meal, _label in _mapping.items():
        _NORMALIZED[_normalize(_label)] = _meal
_NORMALIZED.update({"petit dejeuner": MEAL_BREAKFAST, "dejeuner": MEAL_LUNCH, "diner": MEAL_DINNER})


def meal_type_from_labels(*labels: str | None) -> int | None:
    """Resolve a meal id from any known label (French, Arabic or English)."""
    for label in labels:
        if not label:
            continue
        meal = _NORMALIZED.get(_normalize(label))
        if meal is not None:
            return meal
    return None


def meal_label(meal: int, lang: str = "fr") -> str:
    mapping = {"fr": MEAL_LABELS_FR, "ar": MEAL_LABELS_AR, "en": MEAL_LABELS_EN}.get(
        lang, MEAL_LABELS_FR
    )
    return mapping.get(meal, str(meal))


def parse_meals(values: str | Iterable[int]) -> list[int]:
    """Parse ``"1,2,3"`` or ``[1, 2]`` into a validated, sorted, unique list."""
    if isinstance(values, str):
        raw = [part.strip() for part in values.split(",") if part.strip()]
        try:
            numbers = [int(part) for part in raw]
        except ValueError as exc:
            raise ValueError(f"invalid meal list: {values!r}") from exc
    else:
        numbers = [int(value) for value in values]
    unique = sorted(set(numbers))
    if not unique:
        raise ValueError("at least one meal is required")
    invalid = [value for value in unique if value not in ALL_MEALS]
    if invalid:
        raise ValueError(f"invalid meal ids: {invalid} (expected 1, 2 or 3)")
    return unique
