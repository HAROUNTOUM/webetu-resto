"""Typed data structures used across the project."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .meals import meal_label


@dataclass(slots=True)
class StudentContext:
    """Everything needed to talk to the resto API after login."""

    username: str
    token: str = field(repr=False)
    uuid: str
    id_individu: int
    id_etablissement: int
    year_id: int | None = None
    year_code: str | None = None
    dia_id: int | None = None
    wilaya: str | None = None
    residence_id: int | None = None
    residence_name: str | None = None
    expiration: str | None = None


@dataclass(frozen=True, slots=True)
class Depot:
    """A restaurant / residence offered by the resto API."""

    id: int
    name_fr: str
    name_ar: str
    is_ru: bool
    breakfast: bool
    lunch: bool
    dinner: bool

    @property
    def display_name(self) -> str:
        return self.name_fr or self.name_ar or f"depot {self.id}"

    @property
    def label(self) -> str:
        return f"{self.id} - {self.display_name}"

    def serves(self, meal_type: int) -> bool:
        return {
            1: self.breakfast,
            2: self.lunch,
            3: self.dinner,
        }.get(meal_type, False)


@dataclass(frozen=True, slots=True)
class Reservation:
    id: int
    day: date
    meal_type: int | None
    label_fr: str
    label_ar: str
    depot_fr: str
    candelete: bool

    @property
    def label(self) -> str:
        if self.meal_type is not None:
            return meal_label(self.meal_type)
        return self.label_fr or self.label_ar


@dataclass(frozen=True, slots=True)
class BookingItem:
    day: date
    meal_type: int
    depot_id: int

    @property
    def label(self) -> str:
        return meal_label(self.meal_type)

    @property
    def iso_day(self) -> str:
        return self.day.isoformat()

    def payload(self) -> dict[str, object]:
        return {"date_reserve": self.iso_day, "menu_type": self.meal_type, "idDepot": self.depot_id}


@dataclass(frozen=True, slots=True)
class BookingResult:
    day: date | None
    meal_type: int | None
    success: bool
    message: str


@dataclass(slots=True)
class RunReport:
    """Outcome of one booking run. Used by the CLI, the bot and the state file."""

    started_at: datetime
    dates: list[date]
    depot: Depot | None = None
    planned: list[BookingItem] = field(default_factory=list)
    booked: list[BookingItem] = field(default_factory=list)
    skipped: list[BookingItem] = field(default_factory=list)
    failed: list[tuple[BookingItem, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total(self) -> int:
        return len(self.booked) + len(self.failed)

    @property
    def ok(self) -> bool:
        return not self.failed

    @property
    def status(self) -> str:
        if self.dry_run:
            return "dry-run"
        if not self.failed:
            return "ok"
        return "failed" if not self.booked else "partial"
