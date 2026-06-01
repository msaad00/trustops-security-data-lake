"""Tests for atomic lake file writes in :mod:`security_lakehouse.io`."""

from __future__ import annotations

from pathlib import Path

import pytest

from security_lakehouse.io import (
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)


def _tmp_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.tmp"))


def test_write_jsonl_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "events.jsonl"
    rows = [{"b": 2, "a": 1}, {"z": "last", "k": [3, 2, 1]}]

    write_jsonl(target, rows)

    assert read_jsonl(target) == rows
    # serialization is sorted/compact and newline-terminated
    raw = target.read_text(encoding="utf-8")
    assert raw == '{"a":1,"b":2}\n{"k":[3,2,1],"z":"last"}\n'
    assert _tmp_files(target.parent) == []


def test_write_json_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "snapshot.json"
    payload = {"beta": 2, "alpha": {"y": 1, "x": 0}}

    write_json(target, payload)

    assert read_json(target) == payload
    raw = target.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert '"alpha"' in raw and raw.index('"alpha"') < raw.index('"beta"')
    assert _tmp_files(target.parent) == []


def test_write_jsonl_preserves_existing_file_on_error(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    good_rows = [{"a": 1}]
    write_jsonl(target, good_rows)
    original = target.read_text(encoding="utf-8")

    # A row containing a non-JSON-serializable object makes json.dumps raise
    # mid-stream, after the temp file has been opened.
    bad_rows = [{"a": 2}, {"bad": object()}]
    with pytest.raises(TypeError):
        write_jsonl(target, bad_rows)

    assert target.read_text(encoding="utf-8") == original
    assert read_jsonl(target) == good_rows
    assert _tmp_files(target.parent) == []


def test_write_json_preserves_existing_file_on_error(tmp_path: Path) -> None:
    target = tmp_path / "snapshot.json"
    write_json(target, {"ok": True})
    original = target.read_text(encoding="utf-8")

    with pytest.raises(TypeError):
        write_json(target, {"bad": object()})

    assert target.read_text(encoding="utf-8") == original
    assert read_json(target) == {"ok": True}
    assert _tmp_files(target.parent) == []


def test_failed_write_leaves_no_file_when_none_existed(tmp_path: Path) -> None:
    target = tmp_path / "fresh.jsonl"

    with pytest.raises(TypeError):
        write_jsonl(target, [{"bad": object()}])

    assert not target.exists()
    assert _tmp_files(target.parent) == []
