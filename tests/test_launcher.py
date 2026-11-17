from __future__ import annotations

import io
from pathlib import Path

from webetu_resto import launcher


def test_ensure_streams_does_nothing_when_streams_exist(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(launcher, "config_dir", lambda: tmp_path)
    launcher.ensure_streams()
    assert not (tmp_path / launcher.LOG_NAME).exists()


def test_ensure_streams_redirects_to_a_log_file_without_console(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(launcher, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(launcher.sys, "stdout", None)
    monkeypatch.setattr(launcher.sys, "stderr", None)
    monkeypatch.setattr(launcher.sys, "stdin", None)
    launcher.ensure_streams()
    log_stream = launcher.sys.stdout
    stdin_stream = launcher.sys.stdin
    assert log_stream is not None
    print("hello from a windowed program", flush=True)
    assert "hello from a windowed program" in (tmp_path / launcher.LOG_NAME).read_text("utf-8")
    log_stream.close()  # Windows cannot delete a folder that still holds an open file
    if stdin_stream is not None:
        stdin_stream.close()


def test_ensure_streams_keeps_a_working_stream(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(launcher, "config_dir", lambda: tmp_path)
    kept = io.StringIO()
    monkeypatch.setattr(launcher.sys, "stdout", kept)
    monkeypatch.setattr(launcher.sys, "stderr", None)
    launcher.ensure_streams()
    assert launcher.sys.stdout is kept
    assert launcher.sys.stderr is not None
    launcher.sys.stderr.close()
    if launcher.sys.stdin is not None:
        launcher.sys.stdin.close()
