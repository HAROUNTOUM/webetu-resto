"""Shared first-time setup logic, used by both the CLI and the local web UI.

Nothing in this module prompts the user or prints anything, so any front end
(terminal, browser) can call it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .client import WebetuClient
from .models import Depot, StudentContext

if TYPE_CHECKING:
    from .config import Settings

ClientFactory = Callable[..., Any]

CREDENTIAL_KEYS = ("WEBETU_USERNAME", "WEBETU_PASSWORD", "WEBETU_RESTO_ID")


@dataclass(slots=True)
class Verified:
    """Result of a successful credential check."""

    context: StudentContext
    depots: list[Depot]


def verify_and_resolve(
    username: str,
    password: str,
    settings: Settings,
    *,
    client_factory: ClientFactory = WebetuClient,
) -> Verified:
    """Log in, load the student context and list the restaurants.

    Raises ``AuthError`` for wrong credentials, ``NetworkError`` when ONOU is
    unreachable and ``WebetuError`` for anything else. Nothing is written.
    """
    probe = client_factory(
        username,
        password,
        progres_base=settings.webetu_progres_base,
        resto_base=settings.webetu_resto_base,
        hmac_secret=settings.hmac_secret,
        request_interval=settings.webetu_request_interval,
    )
    try:
        probe.login()
        context = probe.load_student_context()
        probe.ensure_resto_session()
        depots = probe.get_depots()
    finally:
        probe.close()
    return Verified(context=context, depots=list(depots))


def env_quote(value: str) -> str:
    """Quote a value for a .env file when it contains special characters."""
    if any(character in value for character in " #'\"\t"):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def write_env(path: Path, values: dict[str, str]) -> None:
    """Merge values into .env, preserving comments and unrelated keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                output.append(f"{key}={env_quote(remaining.pop(key))}")
                continue
        output.append(line)
    if output and output[-1].strip():
        output.append("")
    if not path.exists():
        output.append("# Généré par `webtu setup` — ne jamais committer ce fichier.")
    for key, value in remaining.items():
        output.append(f"{key}={env_quote(value)}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    path.chmod(0o600)


def save_config(path: Path, username: str, password: str, resto_id: int) -> None:
    """Write the three values the daemon needs."""
    write_env(
        path,
        {
            "WEBETU_USERNAME": username,
            "WEBETU_PASSWORD": password,
            "WEBETU_RESTO_ID": str(resto_id),
        },
    )


def clear_config(path: Path) -> bool:
    """Remove the credentials from the .env file. Returns True if it changed."""
    if not path.exists():
        return False
    kept: list[str] = []
    changed = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if stripped and not stripped.startswith("#") and key in CREDENTIAL_KEYS:
            changed = True
            continue
        kept.append(line)
    if changed:
        path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
        path.chmod(0o600)
    return changed
