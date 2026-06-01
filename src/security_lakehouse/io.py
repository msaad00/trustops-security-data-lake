"""File IO helpers for JSON and JSONL lake artifacts."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def read_jsonl(path: str | Path, *, missing_ok: bool = False) -> list[dict[str, Any]]:
    target = Path(path)
    if missing_ok and not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(item)
    return rows


def _atomic_write(output: Path, text_chunks: Iterable[str]) -> None:
    """Write ``text_chunks`` to ``output`` atomically.

    The payload is streamed into a temporary file in the same directory as the
    destination, flushed and fsync'd, then moved into place with
    :func:`os.replace`, which is atomic on POSIX for same-filesystem renames. A
    reader therefore only ever sees the previous complete file or the new
    complete file, never a half-written/truncated one. On any error the temp
    file is removed and the exception re-raised, so a failed write never
    replaces the existing destination.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=output.parent, prefix=output.name + ".", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for chunk in text_chunks:
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, output)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    output = Path(path)
    _atomic_write(
        output,
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
    )


def write_json(path: str | Path, payload: Any) -> None:
    output = Path(path)
    _atomic_write(output, [json.dumps(payload, indent=2, sort_keys=True) + "\n"])


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
