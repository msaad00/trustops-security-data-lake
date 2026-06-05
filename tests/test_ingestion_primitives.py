"""Resilient-pull primitives: watermark, paginate, backoff, merge.

Proves the two load-bearing properties end to end: a re-run over overlapping
data produces no duplicates (idempotency), and a simulated HTTP 429 triggers
backoff then succeeds.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest

from security_lakehouse.connector_runner import _upsert_raw_events
from security_lakehouse.connectors_okta import OktaClient, OktaFixtureClient, collect_okta_evidence
from security_lakehouse.ingestion import backoff
from security_lakehouse.ingestion.merge import dedupe_by_key
from security_lakehouse.ingestion.paginate import paginate
from security_lakehouse.ingestion.watermark import read_watermark, write_watermark

FIXTURE = Path(__file__).parent / "fixtures" / "okta"


# --- watermark --------------------------------------------------------------


def test_watermark_round_trip_latest_wins(tmp_path: Path) -> None:
    assert read_watermark(tmp_path, "okta") is None
    write_watermark(tmp_path, "okta", "cursor-1")
    write_watermark(tmp_path, "aws", "other")
    write_watermark(tmp_path, "okta", "cursor-2")
    assert read_watermark(tmp_path, "okta") == "cursor-2"
    assert read_watermark(tmp_path, "aws") == "other"


# --- paginate ---------------------------------------------------------------


def test_paginate_walks_pages_until_no_cursor() -> None:
    pages = {None: {"items": [1, 2], "next": "a"}, "a": {"items": [3], "next": None}}
    out = list(
        paginate(
            fetch_page=lambda c: pages[c],
            extract_items=lambda p: p["items"],
            next_cursor=lambda p: p["next"],
        )
    )
    assert out == [1, 2, 3]


def test_paginate_respects_max_pages() -> None:
    out = list(
        paginate(
            fetch_page=lambda c: {"items": [1], "next": "loop"},
            extract_items=lambda p: p["items"],
            next_cursor=lambda p: p["next"],
            max_pages=3,
        )
    )
    assert out == [1, 1, 1]


# --- backoff ----------------------------------------------------------------


def test_next_delay_honors_retry_after_and_cap() -> None:
    assert backoff.next_delay(0, retry_after=7, jitter=False) == 7
    assert backoff.next_delay(99, retry_after=999, cap=30) == 30
    assert backoff.next_delay(2, base=1, jitter=False) == 4


def test_retry_succeeds_after_transient_failures() -> None:
    calls = {"n": 0}
    slept: list[float] = []

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError("u", 429, "rate", Message(), None)
        return "ok"

    out = backoff.retry(
        flaky,
        is_retryable=lambda e: isinstance(e, urllib.error.HTTPError) and e.code == 429,
        max_retries=5,
        sleep=slept.append,
    )
    assert out == "ok"
    assert calls["n"] == 3 and len(slept) == 2


def test_retry_does_not_retry_non_retryable() -> None:
    with pytest.raises(ValueError):
        backoff.retry(
            lambda: (_ for _ in ()).throw(ValueError("nope")),
            is_retryable=lambda e: isinstance(e, urllib.error.HTTPError),
            sleep=lambda _s: None,
        )


# --- merge (idempotency) ----------------------------------------------------


def test_dedupe_is_idempotent_over_overlapping_data() -> None:
    rows = [{"id": "a", "v": 1}, {"id": "b", "v": 1}]
    once = dedupe_by_key(rows, key=lambda r: r["id"])
    # Re-run over a superset that re-delivers the same rows (overlap) plus one new.
    twice = dedupe_by_key([*rows, *rows, {"id": "c", "v": 1}], key=lambda r: r["id"])
    assert [r["id"] for r in once] == ["a", "b"]
    assert [r["id"] for r in twice] == ["a", "b", "c"]  # no duplicates


def test_dedupe_recency_last_writer_wins() -> None:
    rows = [{"id": "a", "v": 1, "ts": 1}, {"id": "a", "v": 2, "ts": 2}]
    out = dedupe_by_key(rows, key=lambda r: r["id"], recency=lambda r: r["ts"])
    assert out == [{"id": "a", "v": 2, "ts": 2}]


def test_raw_upsert_is_idempotent_on_rerun(tmp_path: Path) -> None:
    rows = collect_okta_evidence(OktaFixtureClient(FIXTURE))
    raw = tmp_path / "raw" / "connector_events.jsonl"
    first = _upsert_raw_events(raw, rows)
    # Re-running the exact same sync must not double-count.
    second = _upsert_raw_events(raw, rows)
    assert len(first) == len(second)
    on_disk = raw.read_text().strip().splitlines()
    assert len(on_disk) == len(first)


# --- okta 429 backoff (wired into the client) -------------------------------


class _FakeResp:
    def __init__(self, body: object) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self.headers = {"Link": ""}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *_: object) -> bool:
        return False


def test_okta_client_retries_on_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backoff.time, "sleep", lambda _s: None)
    calls = {"n": 0}
    headers = Message()
    headers["Retry-After"] = "1"

    def fake_urlopen(_req, timeout=0):  # noqa: ANN001, ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError("https://org.okta.com", 429, "rate", headers, None)
        return _FakeResp([{"id": "u1"}, {"id": "u2"}])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    users = OktaClient("https://org.okta.com", token="t").users()
    assert [u["id"] for u in users] == ["u1", "u2"]
    assert calls["n"] == 2  # one 429, one success
