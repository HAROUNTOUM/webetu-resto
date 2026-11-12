from __future__ import annotations

import pytest

from webetu_resto.meals import (
    MEAL_BREAKFAST,
    MEAL_DINNER,
    MEAL_LUNCH,
    meal_label,
    meal_type_from_labels,
    parse_meals,
)


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("Petit-déjeuner",), MEAL_BREAKFAST),
        (("petit dejeuner",), MEAL_BREAKFAST),
        (("Déjeuner",), MEAL_LUNCH),
        (("diner",), MEAL_DINNER),
        (("Dîner",), MEAL_DINNER),
        (("فطور",), MEAL_BREAKFAST),
        (("غداء",), MEAL_LUNCH),
        (("عشاء",), MEAL_DINNER),
        (("Breakfast",), MEAL_BREAKFAST),
        (("unknown", "غداء"), MEAL_LUNCH),
        ((None, "Dîner"), MEAL_DINNER),
        (("unknown",), None),
        ((), None),
    ],
)
def test_meal_type_from_labels(labels: tuple[str | None, ...], expected: int | None) -> None:
    assert meal_type_from_labels(*labels) == expected


def test_meal_label_languages() -> None:
    assert meal_label(1) == "Petit-déjeuner"
    assert meal_label(2, "ar") == "غداء"
    assert meal_label(3, "en") == "Dinner"
    assert meal_label(99) == "99"


def test_parse_meals_accepts_string_and_iterable() -> None:
    assert parse_meals("3,1,2,2") == [1, 2, 3]
    assert parse_meals([3, 1]) == [1, 3]
    assert parse_meals("2") == [2]


@pytest.mark.parametrize("value", ["", "0", "4", "a", "1,x", []])
def test_parse_meals_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        parse_meals(value)  # type: ignore[arg-type]
