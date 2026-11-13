from __future__ import annotations

from pathlib import Path

import pytest

from webetu_resto import paths


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("XDG_CONFIG_HOME", "APPDATA", "WEBETU_ENV_FILE", "WEBETU_CONFIG_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_config_dir_linux_uses_xdg(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "linux")
    assert paths.config_dir() == fake_home / ".config" / "webetu-resto"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / "xdg"))
    assert paths.config_dir() == fake_home / "xdg" / "webetu-resto"


def test_config_dir_macos(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    assert paths.config_dir() == fake_home / "Library" / "Application Support" / "webetu-resto"


def test_config_dir_windows(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(fake_home / "AppData"))
    assert paths.config_dir() == fake_home / "AppData" / "webetu-resto"
    monkeypatch.delenv("APPDATA")
    assert paths.config_dir() == fake_home / "AppData" / "Roaming" / "webetu-resto"


def test_config_dir_override(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBETU_CONFIG_DIR", str(fake_home / "custom"))
    assert paths.config_dir() == fake_home / "custom"


def test_env_file_priority(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "linux")
    user_file = paths.config_dir() / ".env"
    # nothing exists: where a new file should be written
    assert paths.resolve_env_file() == user_file

    user_file.parent.mkdir(parents=True)
    user_file.write_text("A=1\n")
    assert paths.resolve_env_file() == user_file

    (fake_home / ".env").write_text("B=2\n")  # project file wins over the user file
    assert paths.resolve_env_file() == Path(".env")

    explicit = fake_home / "explicit.env"
    monkeypatch.setenv("WEBETU_ENV_FILE", str(explicit))
    assert paths.resolve_env_file() == explicit  # explicit wins, even if missing


def test_default_state_path_lives_in_config_dir(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths.sys, "platform", "linux")
    assert paths.default_state_path() == paths.config_dir() / "state.json"
