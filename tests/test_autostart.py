from __future__ import annotations

from pathlib import Path

from webetu_resto import autostart


def test_enable_creates_a_cmd_launcher_and_disable_removes_it(tmp_path: Path) -> None:
    assert autostart.is_enabled(tmp_path) is False
    path = autostart.enable(tmp_path)
    assert path.name == "webetu-resto.cmd"
    assert autostart.is_enabled(tmp_path) is True
    content = path.read_bytes().decode("utf-8")
    assert content.startswith("@echo off\r\n")
    assert "ui --no-browser" in content
    autostart.disable(tmp_path)
    assert autostart.is_enabled(tmp_path) is False
    autostart.disable(tmp_path)  # removing twice is harmless


def test_launch_command_for_a_frozen_program(monkeypatch) -> None:
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart.sys, "executable", "C:\\Apps\\webetu-resto.exe")
    assert autostart.launch_command() == '"C:\\Apps\\webetu-resto.exe" ui --no-browser'


def test_refresh_rewrites_a_stale_launcher(tmp_path: Path) -> None:
    assert autostart.refresh(tmp_path) is False  # nothing installed
    path = autostart.enable(tmp_path)
    assert autostart.refresh(tmp_path) is False  # already up to date
    path.write_text("old content", encoding="utf-8")
    assert autostart.refresh(tmp_path) is True
    assert "ui --no-browser" in path.read_text(encoding="utf-8")


def test_startup_dir_uses_appdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    folder = autostart.startup_dir()
    assert folder.parts[-1] == "Startup"
    assert str(folder).startswith(str(tmp_path))
