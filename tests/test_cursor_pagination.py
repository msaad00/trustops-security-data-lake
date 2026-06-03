"""Cursor-pagination contract tests for the v1 collection API.

These exercise the opaque ``cursor`` query param and the ``next_cursor`` field
the v1 collection envelope now always carries, on top of the existing
offset-based pagination (which is covered in :mod:`tests.test_api_v1`).
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

from security_lakehouse.server import _Handler

ROW_COUNT = 25
LIMIT = 10


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def _seed_lake(lake: Path) -> None:
    (lake / "console.html").write_bytes(b"<!doctype html>")
    _write_jsonl(
        lake / "gold" / "control_posture.jsonl",
        [
            {
                "control_id": f"CTRL-{index:03d}",
                "framework": "SOC 2" if index % 2 == 0 else "NIST AI RMF",
                "owner": "security-platform",
                "risk_score": index,
                "status": "fail" if index % 2 == 0 else "pass",
                "title": f"Control {index}",
            }
            for index in range(ROW_COUNT)
        ],
    )


def _spin(lake: Path) -> ThreadingHTTPServer:
    _seed_lake(lake)

    class Handler(_Handler):
        lake_dir = lake
        dashboard_path = lake / "console.html"
        web_dist = None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _request(server: ThreadingHTTPServer, path: str) -> tuple[int, dict[str, object]]:
    host, port = server.server_address
    req = urllib.request.Request(f"http://{host}:{port}{path}", method="GET")
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return int(resp.status), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode("utf-8"))


def _ids(body: dict[str, object]) -> list[str]:
    return [row["control_id"] for row in body["data"]]  # type: ignore[index]


def test_first_page_returns_next_cursor(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _request(server, f"/api/v1/controls?sort=risk_score&limit={LIMIT}")
        assert status == HTTPStatus.OK
        meta = body["meta"]
        assert meta["count"] == ROW_COUNT
        assert meta["returned"] == LIMIT
        assert meta["offset"] == 0
        assert meta["limit"] == LIMIT
        assert isinstance(meta["next_cursor"], str) and meta["next_cursor"]
        assert _ids(body) == [f"CTRL-{i:03d}" for i in range(LIMIT)]
    finally:
        server.shutdown()


def test_following_cursor_returns_next_page_without_overlap(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        seen: list[str] = []
        path = f"/api/v1/controls?sort=risk_score&limit={LIMIT}"
        pages = 0
        while True:
            status, body = _request(server, path)
            assert status == HTTPStatus.OK
            page_ids = _ids(body)
            assert not (set(page_ids) & set(seen)), "pages must not overlap"
            seen.extend(page_ids)
            pages += 1
            cursor = body["meta"]["next_cursor"]
            if cursor is None:
                break
            path = f"/api/v1/controls?sort=risk_score&limit={LIMIT}&cursor={cursor}"

        assert pages == 3  # 25 rows / 10 per page
        assert seen == [f"CTRL-{i:03d}" for i in range(ROW_COUNT)]
    finally:
        server.shutdown()


def test_final_page_has_null_next_cursor(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        # offset 20 with limit 10 over 25 rows -> last 5 rows, no more pages.
        status, body = _request(server, f"/api/v1/controls?sort=risk_score&limit={LIMIT}&offset=20")
        assert status == HTTPStatus.OK
        assert body["meta"]["returned"] == 5
        assert body["meta"]["next_cursor"] is None
    finally:
        server.shutdown()


def test_cursor_takes_precedence_over_offset(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, first = _request(server, f"/api/v1/controls?sort=risk_score&limit={LIMIT}")
        assert status == HTTPStatus.OK
        cursor = first["meta"]["next_cursor"]
        # Bogus offset alongside the cursor: the cursor must win.
        status, body = _request(server, f"/api/v1/controls?sort=risk_score&limit={LIMIT}&offset=0&cursor={cursor}")
        assert status == HTTPStatus.OK
        assert body["meta"]["offset"] == LIMIT
        assert _ids(body) == [f"CTRL-{i:03d}" for i in range(LIMIT, 2 * LIMIT)]
    finally:
        server.shutdown()


def test_invalid_cursor_returns_bad_request_envelope(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        for bad in ["not-base64!!", "Zm9v", "%7B%22offset%22%3A-1%7D"]:
            status, body = _request(server, f"/api/v1/controls?cursor={bad}")
            assert status == HTTPStatus.BAD_REQUEST
            assert set(body) == {"data", "meta", "errors"}
            assert body["data"] is None
            assert body["meta"]["api_version"] == "v1"
            assert body["errors"]
            assert body["errors"][0]["code"] == "bad_request"
    finally:
        server.shutdown()


def test_cursor_keeps_filters_and_sort_consistent_across_pages(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        # Filter to SOC 2 (even indices), descending risk_score, small pages.
        seen: list[str] = []
        path = "/api/v1/controls?framework=SOC 2&sort=-risk_score&limit=5"
        while True:
            status, body = _request(server, path.replace(" ", "%20"))
            assert status == HTTPStatus.OK
            assert body["meta"]["filters"] == {"framework": ["SOC 2"]}
            assert body["meta"]["sort"] == "-risk_score"
            for row in body["data"]:
                assert row["framework"] == "SOC 2"  # type: ignore[index]
            seen.extend(_ids(body))
            cursor = body["meta"]["next_cursor"]
            if cursor is None:
                break
            path = f"/api/v1/controls?framework=SOC 2&sort=-risk_score&limit=5&cursor={cursor}"

        even_ids = [f"CTRL-{i:03d}" for i in range(ROW_COUNT) if i % 2 == 0]
        assert sorted(seen) == sorted(even_ids)
        # Descending risk_score == descending index for the even rows.
        assert seen == sorted(even_ids, reverse=True)
        assert len(seen) == len(set(seen))  # no overlap
    finally:
        server.shutdown()
