from __future__ import annotations

import http.client
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from webetu_resto.ui import UiError, UiServer


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def state(self) -> dict[str, Any]:
        return {"configured": False}

    def status(self) -> dict[str, Any]:
        raise UiError("network", "ONOU unreachable", 502)

    def verify(self, username: str, password: str) -> dict[str, Any]:
        self.calls.append(("verify", (username, password)))
        return {"depots": [{"id": 68, "name": "RU 68"}]}

    def save(self, resto_id: int) -> dict[str, Any]:
        self.calls.append(("save", resto_id))
        return {"configured": True}

    def run_now(self) -> dict[str, Any]:
        self.calls.append(("run", None))
        return {}

    def set_auto(self, enabled: bool) -> dict[str, Any]:
        self.calls.append(("auto", enabled))
        return {}

    def set_autostart(self, enabled: bool) -> dict[str, Any]:
        self.calls.append(("autostart", enabled))
        return {}

    def forget(self) -> dict[str, Any]:
        self.calls.append(("forget", None))
        return {}


@contextmanager
def running_server() -> Iterator[tuple[UiServer, FakeBackend]]:
    backend = FakeBackend()
    server = UiServer(backend, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, backend
    finally:
        server.shutdown()
        server.server_close()


def request(
    server: UiServer,
    method: str,
    path: str,
    body: Any = None,
    headers: dict[str, str] | None = None,
    *,
    host: str | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    merged = {"Host": host or f"127.0.0.1:{server.port}"}
    merged.update(headers or {})
    payload = json.dumps(body).encode() if body is not None else None
    connection.request(method, path, body=payload, headers=merged)
    response = connection.getresponse()
    data = response.read()
    result = (response.status, {k.lower(): v for k, v in response.getheaders()}, data)
    connection.close()
    return result


def post(server: UiServer, path: str, body: Any, **overrides: str) -> tuple[int, Any]:
    headers = {"Content-Type": "application/json", "X-CSRF-Token": server.csrf_token}
    headers.update(overrides)
    status, _, data = request(server, "POST", path, body, headers)
    try:
        return status, json.loads(data)
    except json.JSONDecodeError:
        return status, None


def test_ping_and_page_are_served_on_localhost_only() -> None:
    with running_server() as (server, _):
        assert server.server_address[0] == "127.0.0.1"
        status, _, data = request(server, "GET", "/api/ping")
        assert status == 200
        assert json.loads(data)["app"] == "webetu-resto"
        status, headers, data = request(server, "GET", "/")
        assert status == 200
        page = data.decode("utf-8")
        assert server.csrf_token in page
        assert "__CSRF__" not in page and "__NONCE__" not in page
        assert "script-src 'nonce-" in headers["content-security-policy"]
        assert headers["cache-control"] == "no-store"


def test_foreign_host_header_is_rejected() -> None:
    with running_server() as (server, _):
        for host in ("evil.example", f"evil.example:{server.port}", "127.0.0.1"):
            status, _, _ = request(server, "GET", "/api/state", host=host)
            assert status == 403


def test_post_requires_csrf_token_and_json() -> None:
    with running_server() as (server, backend):
        status, _ = post(server, "/api/run", {}, **{"X-CSRF-Token": "wrong"})
        assert status == 403
        status, _ = post(server, "/api/run", {}, **{"Content-Type": "text/plain"})
        assert status == 403
        status, _ = post(server, "/api/run", {}, Origin="http://evil.example")
        assert status == 403
        assert backend.calls == []
        status, body = post(server, "/api/run", {})
        assert status == 200 and body["ok"] is True
        assert backend.calls == [("run", None)]


def test_verify_passes_credentials_and_strips_matricule() -> None:
    with running_server() as (server, backend):
        status, body = post(server, "/api/verify", {"username": " 2022001 ", "password": " p w "})
        assert status == 200
        assert body["data"]["depots"][0]["id"] == 68
        assert backend.calls == [("verify", ("2022001", " p w "))]


def test_backend_errors_become_json_errors() -> None:
    with running_server() as (server, _):
        status, _, data = request(server, "GET", "/api/status")
        body = json.loads(data)
        assert status == 502
        assert body == {"ok": False, "error": {"code": "network", "message": "ONOU unreachable"}}


def test_validation_of_payloads() -> None:
    with running_server() as (server, backend):
        assert post(server, "/api/save", {"resto_id": "68"})[0] == 400
        assert post(server, "/api/save", {"resto_id": True})[0] == 400
        assert post(server, "/api/auto", {"enabled": "yes"})[0] == 400
        assert post(server, "/api/verify", {"username": "a"})[0] == 400
        assert post(server, "/api/verify", {"username": "a", "password": "x" * 500})[0] == 400
        assert backend.calls == []
        assert post(server, "/api/save", {"resto_id": 68})[0] == 200
        assert post(server, "/api/auto", {"enabled": False})[0] == 200
        assert post(server, "/api/autostart", {"enabled": True})[0] == 200
        assert post(server, "/api/forget", {})[0] == 200
        assert [name for name, _ in backend.calls] == ["save", "auto", "autostart", "forget"]


def test_oversized_and_malformed_bodies_are_rejected() -> None:
    with running_server() as (server, _):
        headers = {"Content-Type": "application/json", "X-CSRF-Token": server.csrf_token}
        status, _, _ = request(
            server, "POST", "/api/run", None, {**headers, "Content-Length": "99999"}
        )
        assert status == 413
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        connection.request(
            "POST",
            "/api/run",
            body=b"not json",
            headers={**headers, "Host": f"127.0.0.1:{server.port}"},
        )
        assert connection.getresponse().status == 400
        connection.close()


def test_unknown_routes_are_404() -> None:
    with running_server() as (server, _):
        assert request(server, "GET", "/nope")[0] == 404
        assert post(server, "/api/nope", {})[0] == 404


def test_quit_stops_the_server() -> None:
    backend = FakeBackend()
    server = UiServer(backend, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    status, body = post(server, "/api/quit", {})
    assert status == 200 and body["ok"] is True
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert server.quit_requested
    server.server_close()


def test_translate_error_maps_project_errors_to_codes() -> None:
    from webetu_resto.errors import (
        ApiError,
        AuthError,
        ConfigError,
        NetworkError,
        WebetuError,
    )
    from webetu_resto.ui import translate_error

    assert translate_error(AuthError("x")).code == "bad_credentials"
    assert translate_error(AuthError("x")).status == 401
    assert translate_error(NetworkError("x")).code == "network"
    assert translate_error(ConfigError("x")).code == "config"
    api = translate_error(ApiError("GET", "/secret/path", 503, "private body"))
    assert api.code == "server"
    assert "private body" not in api.message and "/secret/path" not in api.message
    housing = translate_error(WebetuError("aucune demande d'hébergement trouvée pour l'année 2026"))
    assert housing.code == "no_residence"
    assert translate_error(WebetuError("autre chose")).code == "unknown"
