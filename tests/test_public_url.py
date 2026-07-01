"""Tests for public base URL normalization."""

from __future__ import annotations

from security_lakehouse.public_url import normalize_public_url


def test_normalize_public_url_accepts_https() -> None:
    assert normalize_public_url("https://trustops.example.test/") == "https://trustops.example.test"


def test_normalize_public_url_allows_local_http() -> None:
    assert normalize_public_url("http://localhost:8080/console") == "http://localhost:8080/console"


def test_normalize_public_url_rejects_http_remote() -> None:
    assert normalize_public_url("http://trustops.example.test") is None


def test_normalize_public_url_rejects_credentials() -> None:
    assert normalize_public_url("https://user:pass@trustops.example.test") is None


def test_normalize_public_url_rejects_javascript_scheme() -> None:
    assert normalize_public_url("javascript:alert(1)") is None
