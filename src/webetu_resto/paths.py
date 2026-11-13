"""Where the tool keeps its configuration and state.

A globally installed ``webtu`` must find the same credentials from any folder,
so the default location is the per-user config directory. A ``.env`` in the
current folder (project / Docker use) still takes precedence.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR = "webetu-resto"


def config_dir() -> Path:
    """Per-user config directory (created on demand by the writers)."""
    override = os.environ.get("WEBETU_CONFIG_DIR", "").strip()
    if override:
        return Path(override)
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "").strip()
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / APP_DIR
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    return (Path(xdg) if xdg else Path.home() / ".config") / APP_DIR


def resolve_env_file() -> Path:
    """The env file to read, or (when none exists yet) where to create it.

    Order: ``WEBETU_ENV_FILE`` > ``./.env`` > ``<config dir>/.env``.
    """
    explicit = os.environ.get("WEBETU_ENV_FILE", "").strip()
    if explicit:
        return Path(explicit)
    local = Path(".env")
    if local.is_file():
        return local
    return config_dir() / ".env"


def default_state_path() -> Path:
    return config_dir() / "state.json"
