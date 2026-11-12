"""Typed exceptions.

Rule: an error message must never contain a password, a JWT, a resto token or
any other credential. Only paths, HTTP statuses and short response bodies are
allowed, and bodies are truncated.
"""

from __future__ import annotations


class WebetuError(Exception):
    """Base class for every error raised by this project."""


class ConfigError(WebetuError):
    """Invalid or incomplete configuration (usually .env)."""


class AuthError(WebetuError):
    """The matricule/password pair was rejected."""


class NetworkError(WebetuError):
    """The network request failed after all retries."""


class RestoSessionError(WebetuError):
    """The resto session could not be opened."""


class ApiError(WebetuError):
    """The API answered with an unexpected HTTP status."""

    def __init__(self, method: str, path: str, status: int, body: str = "") -> None:
        self.method = method
        self.path = path
        self.status = status
        self.body = (body or "")[:300]
        super().__init__(f"{method} {path} -> HTTP {status}: {self.body!r}")

    @property
    def retryable(self) -> bool:
        return self.status == 429 or self.status >= 500
