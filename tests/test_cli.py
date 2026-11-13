from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from webetu_resto import cli
from webetu_resto.cli import _env_quote, _write_env, app
from webetu_resto.config import Settings
from webetu_resto.errors import ConfigError

runner = CliRunner()


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("setup", "status", "reserve", "cancel", "daemon"):
        assert command in result.stdout


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_env_quote() -> None:
    assert _env_quote("simple") == "simple"
    assert _env_quote("with space") == '"with space"'
    assert _env_quote('with"quote') == '"with\\"quote"'
    assert _env_quote("with#hash") == '"with#hash"'


def test_write_env_merges_and_preserves_comments(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("# header\nWEBETU_USERNAME=old\nOTHER=keep\n")
    _write_env(
        path,
        {
            "WEBETU_USERNAME": "new",
            "WEBETU_PASSWORD": "secret",
            "WEBETU_RESTO_ID": "68",
        },
    )
    text = path.read_text()
    assert "# header" in text
    assert "WEBETU_USERNAME=new" in text
    assert "WEBETU_PASSWORD=secret" in text
    assert "OTHER=keep" in text
    assert "WEBETU_RESTO_ID=68" in text
    if sys.platform != "win32":  # POSIX permission bits do not exist on Windows
        assert path.stat().st_mode & 0o777 == 0o600
    assert text.count("WEBETU_USERNAME=") == 1


def test_write_env_creates_file(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    _write_env(path, {"WEBETU_USERNAME": "u"})
    assert "WEBETU_USERNAME=u" in path.read_text()
    assert "ne jamais committer" in path.read_text()


def test_bot_command_is_gone() -> None:
    result = runner.invoke(app, ["bot"])
    assert result.exit_code != 0


def test_ensure_credentials_returns_existing_without_prompt(monkeypatch) -> None:
    settings = Settings(_env_file=None, webetu_username="u", webetu_password="p")
    monkeypatch.setattr(cli, "_run_setup", lambda *a, **k: pytest.fail("must not prompt"))
    assert cli._ensure_credentials(settings) is settings


def test_ensure_credentials_non_interactive_raises(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_is_interactive", lambda: False)
    with pytest.raises(ConfigError):
        cli._ensure_credentials(Settings(_env_file=None))


def test_ensure_credentials_prompts_on_first_connection(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def fake_setup(current: Settings, *, change_resto: bool = False) -> None:
        calls.append("setup")

    monkeypatch.setattr(cli, "_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_run_setup", fake_setup)
    monkeypatch.setattr(
        cli,
        "_load_settings",
        lambda: Settings(_env_file=None, webetu_username="123", webetu_password="pw"),
    )
    result = cli._ensure_credentials(Settings(_env_file=None))
    assert calls == ["setup"]
    assert result.webetu_username == "123"
    assert result.password == "pw"


def test_run_setup_writes_env_after_verifying_login(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WEBETU_ENV_FILE", str(tmp_path / ".env"))

    class FakeDepot:
        id = 68
        label = "RU 68"
        is_ru = True

    class FakeContext:
        residence_name = "Résidence"

    class FakeClient:
        def __init__(self, username: str, password: str, **_: object) -> None:
            assert (username, password) == ("2022001", "pw")

        def login(self) -> None: ...
        def load_student_context(self) -> FakeContext:
            return FakeContext()

        def ensure_resto_session(self) -> str:
            return "t"

        def get_depots(self) -> list[FakeDepot]:
            return [FakeDepot()]

        def close(self) -> None: ...

    monkeypatch.setattr(cli, "WebetuClient", FakeClient)
    answers = iter(["2022001", "pw"])
    monkeypatch.setattr(cli.typer, "prompt", lambda *a, **k: next(answers))
    cli._run_setup(Settings(_env_file=None))
    text = (tmp_path / ".env").read_text()
    assert "WEBETU_USERNAME=2022001" in text
    assert "WEBETU_PASSWORD=pw" in text
    assert "WEBETU_RESTO_ID=68" in text


def test_configure_stdio_tolerates_streams_without_reconfigure(monkeypatch) -> None:
    class Plain:
        def write(self, _text: str) -> int:
            return 0

    monkeypatch.setattr(cli.sys, "stdout", Plain())
    monkeypatch.setattr(cli.sys, "stderr", Plain())
    cli._configure_stdio()


def test_configure_stdio_sets_utf8(monkeypatch) -> None:
    seen: dict[str, object] = {}

    class Stream:
        def reconfigure(self, **kwargs: object) -> None:
            seen.update(kwargs)

    monkeypatch.setattr(cli.sys, "stdout", Stream())
    monkeypatch.setattr(cli.sys, "stderr", Stream())
    cli._configure_stdio()
    assert seen == {"encoding": "utf-8", "errors": "replace"}


def test_run_setup_creates_the_config_directory(monkeypatch, tmp_path) -> None:
    target = tmp_path / "fresh" / "config" / ".env"
    monkeypatch.setenv("WEBETU_ENV_FILE", str(target))
    monkeypatch.setattr(cli, "WebetuClient", _SetupFakeClient)
    answers = iter(["2022001", "pw"])
    monkeypatch.setattr(cli.typer, "prompt", lambda *a, **k: next(answers))
    cli._run_setup(Settings(_env_file=None))
    assert "WEBETU_USERNAME=2022001" in target.read_text()


def test_debug_config_shows_env_file_location(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WEBETU_ENV_FILE", str(tmp_path / "missing.env"))
    result = runner.invoke(app, ["debug-config"])
    assert result.exit_code == 0
    assert "missing.env" in result.stdout
    assert "env_file_exists" in result.stdout
    assert "password" not in result.stdout.lower()


class _SetupFakeDepot:
    id = 68
    label = "RU 68"
    is_ru = True


class _SetupFakeClient:
    def __init__(self, username: str, password: str, **_: object) -> None:
        pass

    def login(self) -> None: ...

    def load_student_context(self) -> object:
        return type("Ctx", (), {"residence_name": "Résidence"})()

    def ensure_resto_session(self) -> str:
        return "t"

    def get_depots(self) -> list[_SetupFakeDepot]:
        return [_SetupFakeDepot()]

    def close(self) -> None: ...
