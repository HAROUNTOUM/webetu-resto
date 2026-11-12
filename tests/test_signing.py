from __future__ import annotations

import pytest

from webetu_resto.signing import DEFAULT_HMAC_SECRET, make_signature_headers, sign


def test_sign_matches_golden_vector() -> None:
    assert (
        sign("secret", "1700000000", "abc-123", '{"a":1}')
        == "c9e0292c54dbe6fb59f889223317ffb84468af5401d05051c986160dd02804b0"
    )


def test_sign_empty_body_with_app_key() -> None:
    assert (
        sign(DEFAULT_HMAC_SECRET, "1700000000", "nonce", "")
        == "0e016b9be14a3df90fcffeed3674da47c65e592ea7356a90511fdfa2933becbc"
    )


def test_sign_keeps_unicode_as_utf8() -> None:
    assert (
        sign("secret", "1", "n", "héllo")
        == "5bf817a973d5f7949fa5db6ca8ea9f4ab3684543ae060b8ea3ae0aeaded53842"
    )


def test_sign_accepts_bytes_key() -> None:
    assert sign(b"secret", "1", "n", "") == sign("secret", "1", "n", "")


def test_make_headers_is_deterministic_with_injected_values() -> None:
    headers = make_signature_headers("secret", '{"a":1}', timestamp=1700000000, nonce="abc-123")
    assert headers == {
        "X-Timestamp": "1700000000",
        "X-Nonce": "abc-123",
        "X-Signature": "c9e0292c54dbe6fb59f889223317ffb84468af5401d05051c986160dd02804b0",
    }


def test_make_headers_generates_uuid_nonce() -> None:
    headers = make_signature_headers("secret", "")
    assert len(headers["X-Nonce"]) == 36
    assert headers["X-Signature"] == sign("secret", headers["X-Timestamp"], headers["X-Nonce"], "")


@pytest.mark.parametrize("body", ["", "{}", '{"x":"é"}'])
def test_signature_depends_on_exact_body(body: str) -> None:
    assert sign("k", "1", "n", body) != sign("k", "1", "n", body + " ")
