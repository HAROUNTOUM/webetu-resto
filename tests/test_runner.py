from __future__ import annotations

from datetime import date

import pytest

from webetu_resto import runner
from webetu_resto.errors import ConfigError
from webetu_resto.models import (
    BookingItem,
    BookingResult,
    Depot,
    Reservation,
    RunReport,
    StudentContext,
)
from webetu_resto.runner import RunOptions, fetch_snapshot, run_once, run_with_prefs
from webetu_resto.state import StateStore


class FakeClient:
    def __init__(
        self,
        *,
        depots: list[Depot],
        reservations: list[Reservation] | None = None,
        results: list[BookingResult] | None = None,
        **kwargs: object,
    ) -> None:
        self.kwargs = kwargs
        self.depots = depots
        self.reservations = reservations or []
        self.results = results
        self.session: StudentContext | None = None
        self.reserved: list[BookingItem] = []
        self.closed = False
        self.resto_ready = False

    def login(self) -> StudentContext:
        self.session = StudentContext(
            username="u",
            token="jwt",
            uuid="uuid",
            id_individu=1,
            id_etablissement=2,
            year_id=25,
            year_code="2026/2027",
            dia_id=3,
            wilaya="06",
            residence_id=5550001,
            residence_name="Résidence",
        )
        return self.session

    def load_student_context(self) -> StudentContext:
        assert self.session is not None
        return self.session

    def ensure_resto_session(self) -> str:
        self.resto_ready = True
        return "resto"

    def get_depots(self) -> list[Depot]:
        return self.depots

    def list_reservations(self) -> list[Reservation]:
        return self.reservations

    def reserve(self, items: list[BookingItem]) -> list[BookingResult]:
        self.reserved = list(items)
        if self.results is not None:
            return self.results
        return [BookingResult(item.day, item.meal_type, True, "ok") for item in self.reserved]

    def close(self) -> None:
        self.closed = True


def _options(**overrides: object) -> RunOptions:
    values: dict[str, object] = {
        "username": "u",
        "password": "p",
        "resto_id": 68,
        "book_days": [1, 2],
        "meals": [1, 2],
        "today": date(2026, 11, 12),
        "request_interval": 0,
    }
    values.update(overrides)
    return RunOptions(**values)  # type: ignore[arg-type]


def _factory(
    depots: list[Depot],
    reservations: list[Reservation] | None = None,
    results: list[BookingResult] | None = None,
):
    created: list[FakeClient] = []

    def factory(**kwargs: object) -> FakeClient:
        client = FakeClient(depots=depots, reservations=reservations, results=results, **kwargs)
        created.append(client)
        return client

    return factory, created


def test_run_once_dry_run(depot: Depot) -> None:
    factory, created = _factory([depot])
    report = run_once(_options(dry_run=True), factory=factory)
    assert report.dry_run
    assert report.depot == depot
    assert len(report.planned) == 4
    assert report.booked == []
    assert created[0].reserved == []
    assert created[0].closed
    assert created[0].resto_ready


def test_run_once_books_missing(depot: Depot) -> None:
    factory, created = _factory([depot])
    report = run_once(_options(), factory=factory)
    assert report.status == "ok"
    assert len(report.booked) == 4
    assert report.failed == []
    assert len(created[0].reserved) == 4


def test_run_once_skips_existing(depot: Depot, existing: list[Reservation]) -> None:
    factory, _ = _factory([depot], reservations=existing)
    report = run_once(_options(), factory=factory)
    assert len(report.skipped) == 1
    assert len(report.booked) == 3
    assert report.status == "ok"


def test_run_once_auto_detects_restaurant(depot: Depot) -> None:
    factory, _ = _factory([depot])
    report = run_once(_options(resto_id=None), factory=factory)
    assert report.depot is not None
    assert report.depot.id == 68


def test_run_once_ambiguous_restaurant_closes_client(depot: Depot) -> None:
    depots = [depot, Depot(1, "AUTRE", "", True, True, True, True)]
    factory, created = _factory(depots)
    with pytest.raises(ConfigError, match="plusieurs"):
        run_once(_options(resto_id=None), factory=factory)
    assert created[0].closed


def test_run_once_partial_failure(depot: Depot) -> None:
    results = [
        BookingResult(date(2026, 11, 13), 1, True, "ok"),
        BookingResult(date(2026, 11, 13), 2, False, "refusé"),
    ]
    factory, _ = _factory([depot], results=results)
    report = run_once(_options(book_days=[1]), factory=factory)
    assert report.status == "partial"
    assert len(report.booked) == 1
    assert len(report.failed) == 1


def test_fetch_snapshot(depot: Depot, existing: list[Reservation]) -> None:
    factory, created = _factory([depot], reservations=existing)
    snapshot = fetch_snapshot(_options(), factory=factory)
    assert snapshot.depot == depot
    assert snapshot.reservations == existing
    assert snapshot.context.username == "u"
    assert created[0].closed


def test_run_with_prefs_uses_overrides_and_records_state(
    settings, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    store = StateStore(tmp_path / "state.json")
    captured: dict[str, RunOptions] = {}

    def fake_run(options: RunOptions, *, factory=None) -> RunReport:  # type: ignore[no-untyped-def]
        captured["options"] = options
        item = BookingItem(options.target_days[0], options.meals[0], 479)  # type: ignore[index]
        return RunReport(
            started_at=__import__("datetime").datetime(2026, 11, 12, 0, 5),
            dates=options.target_days or [],
            booked=[item],
        )

    monkeypatch.setattr(runner, "run_once", fake_run)
    report = run_with_prefs(
        settings,
        store,
        target_days=[date(2026, 11, 14)],
        meals=[2],
        resto_id=479,
    )
    options = captured["options"]
    assert options.meals == [2]
    assert options.resto_id == 479
    assert options.target_days == [date(2026, 11, 14)]
    assert report.booked
    assert store.load().last_run is not None
    assert store.load().last_run.status == "ok"


def test_run_with_prefs_does_not_record_dry_runs(
    settings, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    store = StateStore(tmp_path / "state.json")
    report = RunReport(
        started_at=__import__("datetime").datetime(2026, 11, 12, 0, 5),
        dates=[date(2026, 11, 13)],
        planned=[BookingItem(date(2026, 11, 13), 1, 68)],
        dry_run=True,
    )

    monkeypatch.setattr(runner, "run_once", lambda options: report)

    assert run_with_prefs(settings, store, dry_run=True) is report
    assert store.load().last_run is None
