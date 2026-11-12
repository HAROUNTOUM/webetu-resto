from __future__ import annotations

import json
from datetime import date

import httpx
import pytest
import respx

from webetu_resto.client import WebetuClient, compact_json
from webetu_resto.errors import ApiError, AuthError, NetworkError, RestoSessionError, WebetuError
from webetu_resto.models import BookingItem, StudentContext
from webetu_resto.signing import sign

PROGRES = "https://progres.test"
RESTO = "https://resto.test"
SECRET = "secret"

LOGIN_JSON = {
    "token": "jwt-token",
    "uuid": "uuid-1",
    "idIndividu": 111,
    "etablissementId": 222,
    "expirationDate": "2026-11-13T00:00:00",
}

DEPOTS_JSON = {
    "depots": [
        {
            "id": 68,
            "nameFR": "RU EXAMPLE 02",
            "nameAR": "",
            "isRu": 1,
            "breakfast": 1,
            "lunch": 1,
            "dinner": 1,
        },
        {
            "id": 479,
            "nameFR": "RU 479",
            "nameAR": "",
            "isRu": 0,
            "breakfast": 0,
            "lunch": 1,
            "dinner": 1,
        },
    ]
}


def _client(**overrides: object) -> WebetuClient:
    values: dict[str, object] = {
        "username": "u",
        "password": "p",
        "progres_base": PROGRES,
        "resto_base": RESTO,
        "hmac_secret": SECRET,
        "request_interval": 0,
        "max_attempts": 1,
        "http_client": httpx.Client(),
    }
    values.update(overrides)
    return WebetuClient(**values)  # type: ignore[arg-type]


def _session() -> StudentContext:
    return StudentContext(
        username="u",
        token="jwt-token",
        uuid="uuid-1",
        id_individu=111,
        id_etablissement=222,
        year_id=25,
        year_code="2026/2027",
        dia_id=12345678,
        wilaya="06",
        residence_id=5550001,
        residence_name="Résidence",
    )


def _mock_context() -> None:
    respx.get(f"{PROGRES}/api/infos/AnneeAcademiqueEncours").mock(
        return_value=httpx.Response(200, json={"id": 25, "code": "2026/2027"})
    )
    respx.get(f"{PROGRES}/api/infos/bac/uuid-1/anneeAcademique/25/dia").mock(
        return_value=httpx.Response(200, json={"id": 12345678})
    )
    respx.get(f"{PROGRES}/api/infos/wilayaInscription/12345678").mock(
        return_value=httpx.Response(200, text='"06"')
    )
    respx.get(f"{PROGRES}/api/infos/bac/uuid-1/demandesHebregement").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "idAnneeAcademique": 25,
                    "idResidance": 5550001,
                    "llResidanceLatin": "Résidence",
                }
            ],
        )
    )


def _mock_resto_login() -> None:
    respx.post(f"{RESTO}/api/loginpwebetu").mock(
        return_value=httpx.Response(200, json={"token": "resto-token"})
    )


def test_compact_json_matches_app_style() -> None:
    assert compact_json({"a": 1, "b": "é"}) == '{"a":1,"b":"é"}'


@respx.mock
def test_login_stores_session_and_sends_exact_body() -> None:
    route = respx.post(f"{PROGRES}/api/authentication/v1/").mock(
        return_value=httpx.Response(200, json=LOGIN_JSON)
    )
    client = _client()
    session = client.login()
    assert session.token == "jwt-token"
    assert session.uuid == "uuid-1"
    assert session.id_individu == 111
    assert session.expiration == "2026-11-13T00:00:00"
    assert "jwt-token" not in repr(session)
    sent = route.calls[0].request
    assert sent.content == b'{"username":"u","password":"p"}'


@respx.mock
def test_login_rejects_bad_credentials() -> None:
    respx.post(f"{PROGRES}/api/authentication/v1/").mock(
        return_value=httpx.Response(401, json={"message": "bad"})
    )
    with pytest.raises(AuthError):
        _client().login()


@respx.mock
def test_login_incomplete_response() -> None:
    respx.post(f"{PROGRES}/api/authentication/v1/").mock(
        return_value=httpx.Response(200, json={"foo": "bar"})
    )
    with pytest.raises(WebetuError, match="incomplète"):
        _client().login()


@respx.mock
def test_login_server_error_is_api_error() -> None:
    respx.post(f"{PROGRES}/api/authentication/v1/").mock(
        return_value=httpx.Response(500, text="boom")
    )
    with pytest.raises(ApiError) as excinfo:
        _client().login()
    assert excinfo.value.status == 500
    assert "boom" in str(excinfo.value)


@respx.mock
def test_load_student_context() -> None:
    client = _client()
    client.session = StudentContext(
        username="u", token="jwt-token", uuid="uuid-1", id_individu=111, id_etablissement=222
    )
    _mock_context()
    session = client.load_student_context()
    assert session.year_id == 25
    assert session.year_code == "2026/2027"
    assert session.dia_id == 12345678
    assert session.wilaya == "06"
    assert session.residence_id == 5550001
    assert session.residence_name == "Résidence"


@respx.mock
def test_load_student_context_without_housing() -> None:
    client = _client()
    client.session = StudentContext(
        username="u", token="jwt-token", uuid="uuid-1", id_individu=111, id_etablissement=222
    )
    respx.get(f"{PROGRES}/api/infos/AnneeAcademiqueEncours").mock(
        return_value=httpx.Response(200, json={"id": 25, "code": "2026/2027"})
    )
    respx.get(f"{PROGRES}/api/infos/bac/uuid-1/anneeAcademique/25/dia").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    respx.get(f"{PROGRES}/api/infos/wilayaInscription/1").mock(
        return_value=httpx.Response(200, text='"06"')
    )
    respx.get(f"{PROGRES}/api/infos/bac/uuid-1/demandesHebregement").mock(
        return_value=httpx.Response(200, json=[])
    )
    with pytest.raises(WebetuError, match="hébergement"):
        client.load_student_context()


@respx.mock
def test_progres_401_is_auth_error() -> None:
    client = _client()
    client.session = _session()
    respx.get(f"{PROGRES}/api/infos/AnneeAcademiqueEncours").mock(return_value=httpx.Response(401))
    with pytest.raises(AuthError):
        client.load_student_context()


@respx.mock
def test_resto_login_signs_body() -> None:
    client = _client()
    client.session = _session()

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        assert request.headers["Authorization"] == "Bearer jwt-token"
        assert request.headers["X-Signature"] == sign(
            SECRET,
            request.headers["X-Timestamp"],
            request.headers["X-Nonce"],
            body,
        )
        payload = json.loads(body)
        assert payload["uuid"] == "uuid-1"
        assert payload["wilaya"] == "06"
        assert payload["residence"] == 5550001
        assert payload["token"] == "jwt-token"
        return httpx.Response(200, json={"token": "resto-token"})

    respx.post(f"{RESTO}/api/loginpwebetu").mock(side_effect=handler)
    assert client.resto_login() == "resto-token"
    assert client.ensure_resto_session() == "resto-token"
    assert respx.calls.call_count == 1


@respx.mock
def test_resto_login_without_token() -> None:
    client = _client()
    client.session = _session()
    respx.post(f"{RESTO}/api/loginpwebetu").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    with pytest.raises(RestoSessionError):
        client.resto_login()


@respx.mock
def test_resto_401_is_auth_error() -> None:
    client = _client()
    client.session = _session()
    respx.post(f"{RESTO}/api/loginpwebetu").mock(return_value=httpx.Response(401))
    with pytest.raises(AuthError):
        client.resto_login()


@respx.mock
def test_get_depots() -> None:
    client = _client()
    client.session = _session()
    _mock_resto_login()
    respx.get(f"{RESTO}/api/getdepotres").mock(return_value=httpx.Response(200, json=DEPOTS_JSON))
    depots = client.get_depots()
    assert [depot.id for depot in depots] == [68, 479]
    assert depots[0].is_ru is True
    assert depots[0].serves(1)
    assert depots[1].is_ru is False
    assert not depots[1].serves(1)


@respx.mock
def test_list_reservations_follows_pagination() -> None:
    client = _client()
    client.session = _session()
    _mock_resto_login()

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params["page"]
        if page == "1":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": 2,
                            "date_reserve": "2026-11-14",
                            "mealtype_fr": "Déjeuner",
                            "mealtype_ar": "غداء",
                            "depot_fr": "RU EXAMPLE 02",
                            "candelete": True,
                        },
                        {
                            "id": 1,
                            "date_reserve": "2026-11-14",
                            "mealtype_fr": "Petit-déjeuner",
                            "mealtype_ar": "فطور",
                            "depot_fr": "RU EXAMPLE 02",
                            "candelete": False,
                        },
                    ],
                    "meta": {"last_page": 2},
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": 3,
                        "date_reserve": "2026-11-15",
                        "mealtype_fr": "Dîner",
                        "mealtype_ar": "عشاء",
                        "depot_fr": "RU EXAMPLE 02",
                        "candelete": True,
                    }
                ],
                "meta": {"last_page": 2},
            },
        )

    respx.get(f"{RESTO}/api/meal-reservations/student").mock(side_effect=handler)
    reservations = client.list_reservations()
    assert [reservation.id for reservation in reservations] == [1, 2, 3]
    assert [reservation.meal_type for reservation in reservations] == [1, 2, 3]
    assert reservations[0].candelete is False


@respx.mock
def test_list_reservations_accepts_bare_list_and_skips_bad_rows() -> None:
    client = _client()
    client.session = _session()
    _mock_resto_login()
    respx.get(f"{RESTO}/api/meal-reservations/student").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 1,
                    "date_reserve": "not-a-date",
                    "mealtype_fr": "Déjeuner",
                    "candelete": 1,
                },
                {
                    "id": 2,
                    "date_reserve": "2026-11-14",
                    "mealtype_fr": "Inconnu",
                    "mealtype_ar": "",
                    "candelete": 0,
                },
                {"no_id": True},
            ],
        )
    )
    reservations = client.list_reservations()
    assert len(reservations) == 1
    assert reservations[0].meal_type is None
    assert reservations[0].candelete is False


@respx.mock
def test_reserve_sends_signed_details_and_parses_results() -> None:
    client = _client()
    client.session = _session()
    _mock_resto_login()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        captured["body"] = body
        assert request.headers["X-Signature"] == sign(
            SECRET,
            request.headers["X-Timestamp"],
            request.headers["X-Nonce"],
            body,
        )
        payload = json.loads(body)
        assert isinstance(payload["details"], list)
        assert all(isinstance(item, str) for item in payload["details"])
        assert payload["details"] == [
            '{"date_reserve":"2026-11-14","menu_type":1,"idDepot":68}',
            '{"date_reserve":"2026-11-14","menu_type":2,"idDepot":68}',
        ]
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": [
                    {"date": "2026-11-14", "meal": "فطور", "status": 1, "message": "ok"},
                    {"date": "2026-11-14", "meal": "غداء", "status": 0, "message": "refusé"},
                ],
            },
        )

    respx.post(f"{RESTO}/api/reservemeal").mock(side_effect=handler)
    items = [
        BookingItem(date(2026, 11, 14), 1, 68),
        BookingItem(date(2026, 11, 14), 2, 68),
    ]
    results = client.reserve(items)
    assert "details" in str(captured["body"])
    assert results[0].success is True
    assert results[0].meal_type == 1
    assert results[1].success is False
    assert results[1].message == "refusé"


@respx.mock
def test_reserve_without_details_raises_server_message() -> None:
    client = _client()
    client.session = _session()
    _mock_resto_login()
    respx.post(f"{RESTO}/api/reservemeal").mock(
        return_value=httpx.Response(422, json={"message": "invalid details"})
    )
    with pytest.raises(ApiError) as excinfo:
        client.reserve([BookingItem(date(2026, 11, 14), 1, 68)])
    assert excinfo.value.status == 422
    assert "invalid details" in str(excinfo.value)


@respx.mock
def test_reserve_empty_list_does_not_call_api() -> None:
    client = _client()
    client.session = _session()
    assert client.reserve([]) == []
    assert respx.calls.call_count == 0


@respx.mock
def test_cancel_signs_body() -> None:
    client = _client()
    client.session = _session()
    _mock_resto_login()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        body = request.content.decode()
        assert request.headers["X-Signature"] == sign(
            SECRET,
            request.headers["X-Timestamp"],
            request.headers["X-Nonce"],
            body,
        )
        return httpx.Response(200, json={"message": "annulée"})

    respx.delete(f"{RESTO}/api/reservemeal/65102937").mock(side_effect=handler)
    assert client.cancel(65102937)["message"] == "annulée"


@respx.mock
def test_retry_on_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("webetu_resto.client.time.sleep", lambda _: None)
    route = respx.post(f"{PROGRES}/api/authentication/v1/").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=LOGIN_JSON),
        ]
    )
    client = _client(max_attempts=2)
    client.login()
    assert route.calls.call_count == 2


@respx.mock
def test_network_error_after_attempts() -> None:
    respx.post(f"{PROGRES}/api/authentication/v1/").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(NetworkError, match="POST /api/authentication/v1/"):
        _client().login()


@respx.mock
def test_invalid_json_is_api_error() -> None:
    respx.post(f"{PROGRES}/api/authentication/v1/").mock(
        return_value=httpx.Response(200, text="<html>")
    )
    with pytest.raises(ApiError, match="HTTP 200"):
        _client().login()


@respx.mock
def test_resto_transient_401_is_retried_with_fresh_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("webetu_resto.client.time.sleep", lambda _s: None)
    client = _client(max_attempts=3)
    client.session = _session()
    route = respx.post(f"{RESTO}/api/loginpwebetu").mock(
        side_effect=[httpx.Response(401), httpx.Response(200, json={"token": "resto-token"})]
    )
    assert client.resto_login() == "resto-token"
    assert route.call_count == 2
    nonces = {call.request.headers["X-Nonce"] for call in route.calls}
    assert len(nonces) == 2


@respx.mock
def test_resto_persistent_401_raises_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("webetu_resto.client.time.sleep", lambda _s: None)
    client = _client(max_attempts=3)
    client.session = _session()
    route = respx.post(f"{RESTO}/api/loginpwebetu").mock(return_value=httpx.Response(403))
    with pytest.raises(AuthError):
        client.resto_login()
    assert route.call_count == 3
