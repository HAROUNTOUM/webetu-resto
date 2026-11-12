"""HTTP client for the Webetu (progres) and ONOU (resto) APIs.

Reverse-engineered from the public Android app. Two different services are
involved:

* ``api-webetu.mesrs.dz`` - login and student data,
  ``Authorization: <jwt>`` (raw, no ``Bearer`` prefix).
* ``gs-api.onou.dz`` - meal reservations,
  ``Authorization: Bearer <jwt>`` plus HMAC headers.

The HMAC covers the exact request body, so the body is serialized once and the
same bytes are signed and sent.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import httpx

from .errors import ApiError, AuthError, NetworkError, RestoSessionError, WebetuError
from .meals import meal_type_from_labels
from .models import BookingItem, BookingResult, Depot, Reservation, StudentContext
from .signing import DEFAULT_HMAC_SECRET, make_signature_headers

logger = logging.getLogger(__name__)

PROGRES_BASE = "https://api-webetu.mesrs.dz"
RESTO_BASE = "https://gs-api.onou.dz"

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def compact_json(payload: object) -> str:
    """Serialize exactly like the mobile app (no spaces, UTF-8 kept as-is)."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "oui"}
    return False


def _parse_day(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _require_mapping(data: object, what: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise WebetuError(f"réponse inattendue de {what}: objet JSON attendu")
    return data


class WebetuClient:
    """Synchronous client. The bot calls it through ``asyncio.to_thread``."""

    def __init__(
        self,
        username: str,
        password: str,
        *,
        progres_base: str = PROGRES_BASE,
        resto_base: str = RESTO_BASE,
        hmac_secret: str = DEFAULT_HMAC_SECRET,
        timeout: float = 20.0,
        request_interval: float = 0.0,
        max_attempts: int = 3,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.username = username
        self._password = password
        self.progres_base = progres_base.rstrip("/")
        self.resto_base = resto_base.rstrip("/")
        self._hmac_secret = hmac_secret
        self._request_interval = max(0.0, request_interval)
        self._max_attempts = max(1, max_attempts)
        self._last_request_at = 0.0
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=False,
        )
        self.session: StudentContext | None = None
        self._resto_token: str | None = None

    # ------------------------------------------------------------- lifecycle

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> WebetuClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ---------------------------------------------------------------- helpers

    def _require_session(self) -> StudentContext:
        if self.session is None:
            raise WebetuError("login() doit être appelé avant cette opération")
        return self.session

    def _throttle(self) -> None:
        if self._request_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self._request_interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _send(
        self,
        method: str,
        url: str,
        *,
        path_label: str,
        headers: dict[str, str],
        content: bytes | None = None,
        params: dict[str, str | int | float | bool | None] | None = None,
    ) -> httpx.Response:
        """Send a request with polite retries. Never logs query strings."""
        for attempt in range(self._max_attempts):
            self._throttle()
            try:
                response = self._http.request(
                    method,
                    url,
                    headers=headers,
                    content=content,
                    params=params,
                )
            except httpx.HTTPError as exc:
                if attempt + 1 >= self._max_attempts:
                    raise NetworkError(
                        f"{method} {path_label} a échoué ({type(exc).__name__})"
                    ) from exc
                time.sleep(min(2.0**attempt, 8.0))
                continue

            if response.status_code in _RETRYABLE_STATUSES and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2.0**attempt
                except ValueError:
                    delay = 2.0**attempt
                time.sleep(min(max(delay, 0.5), 10.0))
                continue
            return response

        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def _json(response: httpx.Response, method: str, path: str) -> object:
        try:
            return json.loads(response.content.decode("utf-8") or "null")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(method, path, response.status_code, response.text) from exc

    # ---------------------------------------------------------------- progres

    def _progres_get(self, path: str) -> object:
        session = self._require_session()
        response = self._send(
            "GET",
            self.progres_base + path,
            path_label=path,
            headers={
                "Accept": "application/json",
                "Authorization": session.token,
                "X-IND-ID": str(session.id_individu),
                "X-DIA-ID": str(session.dia_id or ""),
            },
        )
        if response.status_code in (401, 403):
            raise AuthError("session Webetu expirée ou refusée, reconnecte-toi")
        if response.status_code != 200:
            raise ApiError("GET", path, response.status_code, response.text)
        return self._json(response, "GET", path)

    def login(self) -> StudentContext:
        """Authenticate and store the JWT. Safe to call on every run."""
        body = compact_json({"username": self.username, "password": self._password}).encode()
        response = self._send(
            "POST",
            self.progres_base + "/api/authentication/v1/",
            path_label="/api/authentication/v1/",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            content=body,
        )
        if response.status_code in (401, 403):
            raise AuthError("matricule ou mot de passe incorrect")
        if response.status_code != 200:
            raise ApiError("POST", "/api/authentication/v1/", response.status_code, response.text)
        data = _require_mapping(
            self._json(response, "POST", "/api/authentication/v1/"), "l'authentification"
        )
        try:
            token = str(data["token"])
            uuid = str(data["uuid"])
            id_individu = int(data["idIndividu"])
            id_etablissement = int(data["etablissementId"])
        except (KeyError, TypeError, ValueError) as exc:
            raise WebetuError("réponse d'authentification incomplète") from exc

        self.session = StudentContext(
            username=self.username,
            token=token,
            uuid=uuid,
            id_individu=id_individu,
            id_etablissement=id_etablissement,
            expiration=str(data.get("expirationDate") or "") or None,
        )
        self._resto_token = None
        return self.session

    def load_student_context(self) -> StudentContext:
        """Fill academic year, DIA, wilaya and residence into the session."""
        session = self._require_session()

        year = _require_mapping(
            self._progres_get("/api/infos/AnneeAcademiqueEncours"), "l'année académique"
        )
        session.year_id = int(year["id"])
        session.year_code = str(year.get("code") or "") or None

        dia = _require_mapping(
            self._progres_get(
                f"/api/infos/bac/{session.uuid}/anneeAcademique/{session.year_id}/dia"
            ),
            "le dossier DIA",
        )
        session.dia_id = int(dia["id"])

        wilaya = self._progres_get(f"/api/infos/wilayaInscription/{session.dia_id}")
        if isinstance(wilaya, dict):
            wilaya = wilaya.get("code") or wilaya.get("wilaya") or wilaya.get("id") or ""
        session.wilaya = str(wilaya)

        hebergements = self._progres_get(f"/api/infos/bac/{session.uuid}/demandesHebregement")
        entries = hebergements if isinstance(hebergements, list) else []
        match = next(
            (entry for entry in entries if entry.get("idAnneeAcademique") == session.year_id),
            None,
        )
        if match is None:
            raise WebetuError(
                f"aucune demande d'hébergement trouvée pour l'année {session.year_code or session.year_id}"
            )
        session.residence_id = int(match["idResidance"])
        session.residence_name = (
            str(match.get("llResidanceLatin") or match.get("llResidance") or "") or None
        )
        return session

    # ----------------------------------------------------------------- resto

    def _resto_common(self) -> dict[str, str | int | float | bool | None]:
        session = self._require_session()
        if session.residence_id is None or session.wilaya is None:
            raise WebetuError("load_student_context() doit être appelé avant le resto")
        return {
            "uuid": session.uuid,
            "wilaya": session.wilaya,
            "residence": session.residence_id,
            "token": session.token,
        }

    def _resto_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int | float | bool | None] | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> object:
        session = self._require_session()
        raw_body = "" if payload is None else compact_json(payload)

        # The resto API intermittently answers 401/403 to valid requests. A
        # rejected request was not processed, so re-sending it (freshly signed,
        # new timestamp + nonce) is safe even for POST/DELETE.
        for attempt in range(self._max_attempts):
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {session.token}",
                **make_signature_headers(self._hmac_secret, raw_body),
            }
            if payload is not None:
                headers["Content-Type"] = "application/json"

            response = self._send(
                method,
                self.resto_base + path,
                path_label=path,
                headers=headers,
                content=raw_body.encode("utf-8") if payload is not None else None,
                params=params,
            )
            if response.status_code not in (401, 403):
                break
            if attempt + 1 < self._max_attempts:
                time.sleep(min(0.5 * 2.0**attempt, 4.0))
        if response.status_code in (401, 403):
            raise AuthError("session resto refusée (JWT expiré ou login resto manquant)")
        if response.status_code not in (200, 201, 204):
            raise ApiError(method, path, response.status_code, response.text)
        if response.status_code == 204 or not response.content:
            return None
        return self._json(response, method, path)

    def resto_login(self) -> str:
        """Open the resto session. Required before any other resto endpoint."""
        data = self._resto_request("POST", "/api/loginpwebetu", payload=self._resto_common())
        mapping = _require_mapping(data, "login resto")
        token = mapping.get("token")
        if not token:
            raise RestoSessionError("le serveur resto n'a pas renvoyé de token")
        self._resto_token = str(token)
        return self._resto_token

    def ensure_resto_session(self) -> str:
        if self._resto_token:
            return self._resto_token
        return self.resto_login()

    def get_depots(self) -> list[Depot]:
        self.ensure_resto_session()
        data = self._resto_request("GET", "/api/getdepotres", params=self._resto_common())
        mapping = _require_mapping(data, "la liste des restaurants")
        raw_depots = mapping.get("depots")
        if not isinstance(raw_depots, list):
            raise WebetuError("réponse inattendue de la liste des restaurants")
        depots: list[Depot] = []
        for raw in raw_depots:
            if not isinstance(raw, dict) or "id" not in raw:
                continue
            depots.append(
                Depot(
                    id=int(raw["id"]),
                    name_fr=str(raw.get("nameFR") or ""),
                    name_ar=str(raw.get("nameAR") or ""),
                    is_ru=_as_bool(raw.get("isRu")),
                    breakfast=_as_bool(raw.get("breakfast")),
                    lunch=_as_bool(raw.get("lunch")),
                    dinner=_as_bool(raw.get("dinner")),
                )
            )
        return depots

    def list_reservations(self) -> list[Reservation]:
        """Return every reservation, following the API pagination."""
        self.ensure_resto_session()
        reservations: dict[int, Reservation] = {}
        page = 1
        while page <= 20:
            params = {**self._resto_common(), "page": page}
            data = self._resto_request("GET", "/api/meal-reservations/student", params=params)
            if isinstance(data, list):
                raw_items = data
                last_page = 1
            elif isinstance(data, dict):
                raw_items = data.get("data") or []
                meta = data.get("meta") or {}
                try:
                    last_page = int(meta.get("last_page") or 1)
                except (TypeError, ValueError):
                    last_page = 1
            else:
                raise WebetuError("réponse inattendue de la liste des réservations")

            for raw in raw_items:
                if not isinstance(raw, dict) or "id" not in raw:
                    continue
                day = _parse_day(raw.get("date_reserve"))
                if day is None:
                    logger.warning("réservation %s ignorée: date invalide", raw.get("id"))
                    continue
                label_fr = str(raw.get("mealtype_fr") or "")
                label_ar = str(raw.get("mealtype_ar") or "")
                reservations[int(raw["id"])] = Reservation(
                    id=int(raw["id"]),
                    day=day,
                    meal_type=meal_type_from_labels(label_fr, label_ar),
                    label_fr=label_fr,
                    label_ar=label_ar,
                    depot_fr=str(raw.get("depot_fr") or ""),
                    candelete=_as_bool(raw.get("candelete")),
                )

            if page >= last_page:
                break
            page += 1

        return sorted(
            reservations.values(),
            key=lambda reservation: (reservation.day, reservation.meal_type or 0, reservation.id),
        )

    def reserve(self, items: Sequence[BookingItem]) -> list[BookingResult]:
        """Book several meals in one request (the API supports a details list)."""
        if not items:
            return []
        self.ensure_resto_session()
        payload: dict[str, object] = {
            **self._resto_common(),
            "details": [compact_json(item.payload()) for item in items],
        }
        data = self._resto_request("POST", "/api/reservemeal", payload=payload)
        mapping = _require_mapping(data, "la réservation")
        raw_results = mapping.get("data")
        if not isinstance(raw_results, list):
            message = str(mapping.get("message") or "réservation refusée")
            raise WebetuError(message)

        results: list[BookingResult] = []
        for raw in raw_results:
            if not isinstance(raw, dict):
                continue
            results.append(
                BookingResult(
                    day=_parse_day(raw.get("date")),
                    meal_type=meal_type_from_labels(
                        raw.get("meal"), raw.get("mealtype_fr"), raw.get("mealtype_ar")
                    ),
                    success=_as_bool(raw.get("status")),
                    message=str(raw.get("message") or ""),
                )
            )
        return results

    def cancel(self, reservation_id: int) -> dict[str, Any]:
        self.ensure_resto_session()
        data = self._resto_request(
            "DELETE", f"/api/reservemeal/{reservation_id}", payload=self._resto_common()
        )
        return _require_mapping(data, "l'annulation")
