"""Optional "a new version is available" check (GitHub releases)."""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

from . import __version__, _build

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def current_version() -> str:
    return _build.VERSION or __version__


def parse_version(text: str) -> tuple[int, ...] | None:
    cleaned = text.strip().lstrip("vV")
    parts = cleaned.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def is_newer(latest: str, current: str) -> bool:
    new, old = parse_version(latest), parse_version(current)
    if new is None or old is None:
        return False
    return new > old


def fetch_latest(repo: str, *, timeout: float = 5.0) -> dict[str, str] | None:
    """Return ``{"version": ..., "url": ...}`` for the latest release, or None.

    Any problem (offline, no release yet, odd answer) simply returns None.
    """
    if not _REPO_RE.match(repo):
        return None
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "webetu-resto"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data: Any = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    tag = data.get("tag_name")
    url = data.get("html_url")
    if not isinstance(tag, str) or not isinstance(url, str):
        return None
    if not url.startswith("https://github.com/"):
        return None
    return {"version": tag.lstrip("vV"), "url": url}
