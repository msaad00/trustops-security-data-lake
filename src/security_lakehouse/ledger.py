"""Append-only JSONL ledger helpers.

These helpers are intentionally small and storage-neutral: callers own their
domain schema, while the helper adds tamper-evident linkage and idempotent
replay semantics for append-only operational logs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from security_lakehouse.io import append_jsonl, read_jsonl


def canonical_record_hash(record: dict[str, Any], *, hash_field: str = "record_hash") -> str:
    """Return the canonical sha256 for ``record`` excluding ``hash_field``."""
    payload = {key: value for key, value in record.items() if key != hash_field}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_chained_jsonl(
    path: str | Path,
    record: dict[str, Any],
    *,
    idempotency_key: str | None = None,
    prev_field: str = "prev_hash",
    hash_field: str = "record_hash",
) -> dict[str, Any]:
    """Append ``record`` to ``path`` with hash-chain metadata.

    If ``idempotency_key`` already exists in the file, the existing record is
    returned and no duplicate is written. This supports retry-safe API,
    scheduler, CLI, and agent execution without minting conflicting audit rows.
    """
    target = Path(path)
    key = str(idempotency_key or "").strip() or None
    rows = read_jsonl(target, missing_ok=True)
    if key:
        for row in reversed(rows):
            if row.get("idempotency_key") == key:
                return {**row, "idempotent_replay": True}

    prev_hash = None
    if rows:
        prev_hash = rows[-1].get(hash_field)
        if not isinstance(prev_hash, str) or not prev_hash:
            prev_hash = canonical_record_hash(rows[-1], hash_field=hash_field)

    chained = {**record, prev_field: prev_hash}
    if key:
        chained["idempotency_key"] = key
    chained[hash_field] = canonical_record_hash(chained, hash_field=hash_field)
    append_jsonl(target, chained)
    return chained


def verify_chained_jsonl(
    path: str | Path,
    *,
    prev_field: str = "prev_hash",
    hash_field: str = "record_hash",
) -> dict[str, Any]:
    """Verify a JSONL hash chain and return ``ok``, ``length`` and ``issues``."""
    target = Path(path)
    rows = read_jsonl(target, missing_ok=True)
    issues: list[str] = []
    expected_prev: str | None = None
    tip_hash: str | None = None
    for index, row in enumerate(rows):
        recorded_hash = row.get(hash_field)
        recomputed_hash = canonical_record_hash(row, hash_field=hash_field)
        if row.get(prev_field) != expected_prev:
            issues.append(f"entry {index}: {prev_field} breaks the chain")
        if not isinstance(recorded_hash, str) or not recorded_hash:
            issues.append(f"entry {index}: missing {hash_field}")
            tip_hash = recomputed_hash
            expected_prev = recomputed_hash
            continue
        if recorded_hash != recomputed_hash:
            issues.append(f"entry {index}: {hash_field} does not match content")
        tip_hash = recorded_hash
        expected_prev = recorded_hash
    return {"ok": not issues, "length": len(rows), "tip_hash": tip_hash, "issues": issues}
