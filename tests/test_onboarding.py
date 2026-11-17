from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from webetu_resto.errors import AuthError
from webetu_resto.onboarding import clear_config, save_config, verify_and_resolve

SETTINGS = SimpleNamespace(
    webetu_progres_base="https://progres.example",
    webetu_resto_base="https://resto.example",
    hmac_secret="secret",
    webetu_request_interval=0.0,
)


class FakeClient:
    instances: list[FakeClient] = []

    def __init__(self, username: str, password: str, **options: object) -> None:
        self.username = username
        self.password = password
        self.options = options
        self.closed = False
        self.fail = password == "wrong"
        FakeClient.instances.append(self)

    def login(self) -> None:
        if self.fail:
            raise AuthError("matricule ou mot de passe incorrect")

    def load_student_context(self) -> object:
        return SimpleNamespace(residence_name="Résidence X")

    def ensure_resto_session(self) -> str:
        return "token"

    def get_depots(self) -> list[object]:
        return [SimpleNamespace(id=68, label="RU 68", is_ru=True)]

    def close(self) -> None:
        self.closed = True


def test_verify_returns_context_and_depots_and_closes_client() -> None:
    FakeClient.instances.clear()
    result = verify_and_resolve("2022001", "pw", SETTINGS, client_factory=FakeClient)
    assert result.context.residence_name == "Résidence X"
    assert [depot.id for depot in result.depots] == [68]
    client = FakeClient.instances[0]
    assert client.closed
    assert client.options["progres_base"] == "https://progres.example"
    assert client.options["resto_base"] == "https://resto.example"


def test_verify_closes_client_when_login_fails() -> None:
    FakeClient.instances.clear()
    with pytest.raises(AuthError):
        verify_and_resolve("2022001", "wrong", SETTINGS, client_factory=FakeClient)
    assert FakeClient.instances[0].closed


def test_save_config_writes_the_three_values(tmp_path: Path) -> None:
    path = tmp_path / "sub" / ".env"
    save_config(path, "2022001", "pass word", 68)
    text = path.read_text(encoding="utf-8")
    assert "WEBETU_USERNAME=2022001" in text
    assert 'WEBETU_PASSWORD="pass word"' in text
    assert "WEBETU_RESTO_ID=68" in text


def test_clear_config_removes_credentials_only(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text(
        "# note\nWEBETU_USERNAME=1\nWEBETU_PASSWORD=2\nWEBETU_RESTO_ID=3\nWEBETU_RUN_AT=01:00\n",
        encoding="utf-8",
    )
    assert clear_config(path) is True
    text = path.read_text(encoding="utf-8")
    assert "WEBETU_USERNAME" not in text
    assert "WEBETU_PASSWORD" not in text
    assert "WEBETU_RESTO_ID" not in text
    assert "# note" in text
    assert "WEBETU_RUN_AT=01:00" in text


def test_clear_config_without_file_is_a_noop(tmp_path: Path) -> None:
    assert clear_config(tmp_path / "missing.env") is False
