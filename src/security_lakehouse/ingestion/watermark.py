"""Per-connector high-water cursor (watermark) persistence.

An incremental pull needs to remember where it stopped so the next run only
fetches new records. Watermarks are appended to ``gold/watermarks.jsonl``
(append-only, auditable); the latest entry per connector wins on read.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from security_lakehouse.io import append_jsonl, read_jsonl
from security_lakehouse.models import utc_iso

WATERMARKS_FILE = ("gold", "watermarks.jsonl")


def _path(lake_dir: str | Path) -> Path:
    return Path(lake_dir).joinpath(*WATERMARKS_FILE)


def read_watermark(lake_dir: str | Path, connector_id: str) -> str | None:
    """Return the most recently written cursor for ``connector_id`` (or None)."""
    latest: str | None = None
    for row in read_jsonl(_path(lake_dir), missing_ok=True):
        if row.get("connector_id") == connector_id and row.get("cursor") is not None:
            latest = str(row["cursor"])
    return latest


def write_watermark(lake_dir: str | Path, connector_id: str, cursor: str) -> None:
    """Append a new high-water cursor for ``connector_id``."""
    append_jsonl(
        _path(lake_dir),
        {
            "connector_id": connector_id,
            "cursor": cursor,
            "updated_at": utc_iso(datetime.now(UTC)),
        },
    )
