from __future__ import annotations

import io
import json

from webetu_resto import update


def test_parse_and_compare_versions() -> None:
    assert update.parse_version("v1.2.3") == (1, 2, 3)
    assert update.parse_version("0.10") == (0, 10)
    assert update.parse_version("beta") is None
    assert update.is_newer("0.2.0", "0.1.0")
    assert update.is_newer("v0.10.0", "0.9.9")
    assert not update.is_newer("0.1.0", "0.1.0")
    assert not update.is_newer("garbage", "0.1.0")


def test_fetch_latest_rejects_odd_repository_names() -> None:
    assert update.fetch_latest("not a repo") is None
    assert update.fetch_latest("../etc/passwd") is None


def test_fetch_latest_parses_a_release(monkeypatch) -> None:
    payload = {"tag_name": "v0.3.0", "html_url": "https://github.com/me/app/releases/tag/v0.3.0"}

    class Response(io.BytesIO):
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            self.close()

    monkeypatch.setattr(
        update.urllib.request,
        "urlopen",
        lambda request, timeout: Response(json.dumps(payload).encode()),
    )
    assert update.fetch_latest("me/app") == {
        "version": "0.3.0",
        "url": "https://github.com/me/app/releases/tag/v0.3.0",
    }


def test_fetch_latest_ignores_foreign_links_and_failures(monkeypatch) -> None:
    class Response(io.BytesIO):
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            self.close()

    evil = {"tag_name": "v9.9.9", "html_url": "https://evil.example/download"}
    monkeypatch.setattr(
        update.urllib.request,
        "urlopen",
        lambda request, timeout: Response(json.dumps(evil).encode()),
    )
    assert update.fetch_latest("me/app") is None

    def boom(request: object, timeout: float) -> None:
        raise OSError("offline")

    monkeypatch.setattr(update.urllib.request, "urlopen", boom)
    assert update.fetch_latest("me/app") is None


def test_current_version_falls_back_to_the_package_version() -> None:
    assert update.current_version()
