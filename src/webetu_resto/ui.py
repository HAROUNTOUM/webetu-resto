"""Local web interface: a tiny HTTP server that only listens on this computer.

The server itself is pure standard library and knows nothing about Webetu. It
talks to a ``Backend`` (see ``ui_backend.py``), which makes it easy to test.

Security model (the page asks for a password, so this matters):

* it binds to ``127.0.0.1`` only, never to the network;
* every request must carry a ``Host`` header of this exact address, which
  blocks DNS-rebinding attacks from malicious websites;
* every POST needs a secret CSRF token that only the served page knows;
* the password is never sent back to the browser.
"""

from __future__ import annotations

import hmac
import json
import logging
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Protocol
from urllib.parse import urlsplit

from .errors import ApiError, AuthError, ConfigError, NetworkError
from .ui_page import PAGE_HTML

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8765
MAX_BODY_BYTES = 8192
APP_ID = "webetu-resto"


class UiError(Exception):
    """An error that the browser should display, with a stable ``code``."""

    def __init__(self, code: str, message: str = "", status: int = 400) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code
        self.status = status


def translate_error(exc: Exception) -> UiError:
    """Turn a project error into a stable code the page can translate."""
    if isinstance(exc, AuthError):
        return UiError("bad_credentials", str(exc), 401)
    if isinstance(exc, NetworkError):
        return UiError("network", str(exc), 502)
    if isinstance(exc, ConfigError):
        return UiError("config", str(exc), 400)
    if isinstance(exc, ApiError):
        return UiError("server", f"HTTP {exc.status}", 502)
    if "hébergement" in str(exc):
        return UiError("no_residence", str(exc), 422)
    return UiError("unknown", str(exc), 500)


class Backend(Protocol):
    """What the web page can ask for. Every method returns JSON-ready data."""

    def state(self) -> dict[str, Any]: ...

    def status(self) -> dict[str, Any]: ...

    def verify(self, username: str, password: str) -> dict[str, Any]: ...

    def save(self, resto_id: int) -> dict[str, Any]: ...

    def run_now(self) -> dict[str, Any]: ...

    def set_auto(self, enabled: bool) -> dict[str, Any]: ...

    def set_autostart(self, enabled: bool) -> dict[str, Any]: ...

    def forget(self) -> dict[str, Any]: ...


class UiServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, backend: Backend, *, host: str = "127.0.0.1", port: int = DEFAULT_PORT):
        super().__init__((host, port), UiHandler)
        self.backend = backend
        self.csrf_token = secrets.token_urlsafe(32)
        self.quit_requested = False
        real_port = self.server_address[1]
        self.port = real_port
        self.allowed_hosts = {f"127.0.0.1:{real_port}", f"localhost:{real_port}"}

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"


def _text(payload: dict[str, Any], key: str, limit: int = 200) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise UiError("bad_request", f"{key} is required")
    if len(value) > limit:
        raise UiError("bad_request", f"{key} is too long")
    return value


def _flag(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise UiError("bad_request", f"{key} must be true or false")
    return value


def _number(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise UiError("bad_request", f"{key} must be a number")
    return value


class UiHandler(BaseHTTPRequestHandler):
    server: UiServer
    server_version = "webetu-resto-ui"
    sys_version = ""

    # Never log requests: nothing about the user should end up in a log file.
    def log_message(self, format: str, *args: Any) -> None:
        return

    # ------------------------------------------------------------ plumbing

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        extra: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _fail(self, error: UiError) -> None:
        self._json(
            error.status,
            {"ok": False, "error": {"code": error.code, "message": error.message}},
        )

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in self.server.allowed_hosts

    def _csrf_ok(self) -> bool:
        sent = self.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(sent.encode(), self.server.csrf_token.encode()):
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{h}" for h in self.server.allowed_hosts}:
            return False
        content_type = self.headers.get("Content-Type", "")
        return content_type.split(";")[0].strip().lower() == "application/json"

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise UiError("bad_request", "invalid length") from None
        if length < 0 or length > MAX_BODY_BYTES:
            raise UiError("bad_request", "body too large", 413)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise UiError("bad_request", "invalid JSON") from None
        if not isinstance(data, dict):
            raise UiError("bad_request", "JSON object expected")
        return data

    def _page(self) -> None:
        nonce = secrets.token_urlsafe(16)
        html = PAGE_HTML.replace("__NONCE__", nonce).replace("__CSRF__", self.server.csrf_token)
        policy = (
            "default-src 'none'; "
            f"script-src 'nonce-{nonce}'; "
            "style-src 'unsafe-inline'; "
            "img-src data:; "
            "connect-src 'self'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        self._send(
            200,
            html.encode("utf-8"),
            "text/html; charset=utf-8",
            {"Content-Security-Policy": policy, "X-Frame-Options": "DENY"},
        )

    # -------------------------------------------------------------- routes

    def do_GET(self) -> None:
        if not self._host_ok():
            self._send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        path = urlsplit(self.path).path
        backend = self.server.backend
        try:
            if path == "/":
                self._page()
            elif path == "/api/ping":
                self._json(200, {"ok": True, "app": APP_ID})
            elif path == "/api/state":
                self._json(200, {"ok": True, "data": backend.state()})
            elif path == "/api/status":
                self._json(200, {"ok": True, "data": backend.status()})
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")
        except UiError as error:
            self._fail(error)
        except Exception as exc:
            logger.error("unexpected UI error: %s", type(exc).__name__)
            self._fail(UiError("internal", "unexpected error", 500))

    def do_POST(self) -> None:
        if not self._host_ok() or not self._csrf_ok():
            self._send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        path = urlsplit(self.path).path
        backend = self.server.backend
        try:
            payload = self._read_json()
            data: dict[str, Any]
            if path == "/api/verify":
                data = backend.verify(
                    _text(payload, "username").strip(), _text(payload, "password")
                )
            elif path == "/api/save":
                data = backend.save(_number(payload, "resto_id"))
            elif path == "/api/run":
                data = backend.run_now()
            elif path == "/api/auto":
                data = backend.set_auto(_flag(payload, "enabled"))
            elif path == "/api/autostart":
                data = backend.set_autostart(_flag(payload, "enabled"))
            elif path == "/api/forget":
                data = backend.forget()
            elif path == "/api/quit":
                self._json(200, {"ok": True, "data": {}})
                self.server.quit_requested = True
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            self._json(200, {"ok": True, "data": data})
        except UiError as error:
            self._fail(error)
        except Exception as exc:
            logger.error("unexpected UI error: %s", type(exc).__name__)
            self._fail(UiError("internal", "unexpected error", 500))
