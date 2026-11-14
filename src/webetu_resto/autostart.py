"""Start the program automatically when Windows starts (Windows only).

A one-line ``.cmd`` file is placed in the user's Startup folder. No registry
access, no administrator rights, and it is removed by ``disable()``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

LAUNCHER_NAME = "webetu-resto.cmd"


def supported() -> bool:
    return sys.platform == "win32"


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA", "").strip()
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def launch_command() -> str:
    """Command line that starts the interface without opening the browser."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" ui --no-browser'
    executable = Path(sys.executable)
    windowless = executable.with_name("pythonw.exe")
    if windowless.exists():
        executable = windowless
    return f'"{executable}" -m webetu_resto ui --no-browser'


def _script() -> str:
    return f'@echo off\r\nstart "" /min {launch_command()}\r\n'


def launcher_path(directory: Path | None = None) -> Path:
    return (directory or startup_dir()) / LAUNCHER_NAME


def is_enabled(directory: Path | None = None) -> bool:
    return launcher_path(directory).is_file()


def enable(directory: Path | None = None) -> Path:
    path = launcher_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_script(), encoding="utf-8", newline="")
    return path


def disable(directory: Path | None = None) -> None:
    launcher_path(directory).unlink(missing_ok=True)


def refresh(directory: Path | None = None) -> bool:
    """Rewrite the launcher if the program moved. Returns True when rewritten."""
    path = launcher_path(directory)
    if not path.is_file():
        return False
    try:
        current = path.read_bytes().decode("utf-8")
    except OSError:
        return False
    if current == _script():
        return False
    enable(directory)
    return True
