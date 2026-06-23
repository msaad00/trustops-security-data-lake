"""File IO helpers for JSON and JSONL lake artifacts."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def resolve_path(path: str | Path, *, base_dir: str | Path | None = None) -> Path:
    """Return a canonical local path, optionally confined under ``base_dir``.

    Server-mode callers should pass the tenant/lake root as ``base_dir`` before
    reading or writing lake artifacts. That makes the path policy explicit at
    the shared IO boundary and prevents traversal through ``..`` components or
    existing symlink parents. CLI callers can omit ``base_dir`` to keep normal
    local file paths working.
    """
    raw = os.fspath(path)
    if "\x00" in raw:
        raise ValueError("path contains NUL byte")
    # Canonicalization is the guard boundary: server callers pass ``base_dir``
    # below, and the real target must stay under that trusted root before any
    # read/write operation occurs.
    target = Path(os.path.realpath(os.path.abspath(os.path.expanduser(raw))))
    if base_dir is None:
        return target
    root_raw = os.fspath(base_dir)
    if "\x00" in root_raw:
        raise ValueError("base_dir contains NUL byte")
    root = Path(os.path.realpath(os.path.abspath(os.path.expanduser(root_raw))))
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("path is outside allowed root") from exc
    return target


def read_jsonl(
    path: str | Path,
    *,
    missing_ok: bool = False,
    base_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    target = resolve_path(path, base_dir=base_dir)
    # lgtm[py/path-injection]
    if missing_ok and not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    # lgtm[py/path-injection]
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


def write_jsonl(
    path: str | Path,
    rows: Iterable[dict[str, Any]],
    *,
    base_dir: str | Path | None = None,
) -> None:
    output = resolve_path(path, base_dir=base_dir)
    _atomic_write(
        output,
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
    )


def append_jsonl(
    path: str | Path,
    row: dict[str, Any],
    *,
    base_dir: str | Path | None = None,
) -> None:
    """Append one JSON object as a line, durably.

    Used for append-only ledgers: the line is flushed and fsync'd before the
    call returns so a crash cannot lose an acknowledged record. Unlike
    :func:`write_jsonl` this never rewrites existing content.
    """
    output = resolve_path(path, base_dir=base_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
    with output.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path: str | Path, payload: Any, *, base_dir: str | Path | None = None) -> None:
    output = resolve_path(path, base_dir=base_dir)
    _atomic_write(output, [json.dumps(payload, indent=2, sort_keys=True) + "\n"])


def read_json(path: str | Path, *, base_dir: str | Path | None = None) -> Any:
    return json.loads(resolve_path(path, base_dir=base_dir).read_text(encoding="utf-8"))
