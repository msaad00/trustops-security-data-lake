"""Tests for atomic lake file writes in :mod:`security_lakehouse.io`."""

from __future__ import annotations

from pathlib import Path

import pytest

from security_lakehouse.io import (
    read_json,
    read_jsonl,
    resolve_path,
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


def test_base_dir_allows_paths_inside_root(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    target = lake / "gold" / "events.jsonl"
    rows = [{"event_id": "evt-1"}]

    write_jsonl(target, rows, base_dir=lake)

    assert read_jsonl(lake / "gold" / ".." / "gold" / "events.jsonl", base_dir=lake) == rows


def test_base_dir_rejects_paths_outside_root(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    outside = tmp_path / "outside.jsonl"
    outside.write_text('{"event_id":"evt-1"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="outside allowed root"):
        read_jsonl(outside, base_dir=lake)

    with pytest.raises(ValueError, match="outside allowed root"):
        read_jsonl(lake / ".." / "outside.jsonl", base_dir=lake)


def test_base_dir_rejects_symlink_escape(tmp_path: Path) -> None:
    lake = tmp_path / "lake"
    lake.mkdir()
    outside = tmp_path / "outside.jsonl"
    outside.write_text('{"event_id":"evt-1"}\n', encoding="utf-8")
    link = lake / "linked.jsonl"
    link.symlink_to(outside)

    with pytest.raises(ValueError, match="outside allowed root"):
        read_jsonl(link, base_dir=lake)


def test_resolve_path_rejects_nul_byte() -> None:
    with pytest.raises(ValueError, match="NUL byte"):
        resolve_path("lake/gold/events.jsonl\x00")
