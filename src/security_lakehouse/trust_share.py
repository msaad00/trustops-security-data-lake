"""Scoped, revocable, expiring share links for the Trust Center.

The Trust Center is the surface external reviewers (auditors, customers,
prospects) use to verify posture without internal-team-grade access. A
share is a signed token tied to:

  * ``role``     — auditor (read-only, owner/assignee fields redacted)
  * ``scope``    — what subset of posture is visible (currently always
                    "posture_full"; future: per-framework scoping)
  * ``expires_at``
  * ``created_by``

The share table is append-only at ``gold/trust_shares.jsonl``. Revoke
appends a new record with ``revoked_at``. Only the token *hash* is stored;
the raw token returns once at create time.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ALLOWED_ROLES = {"auditor"}
ALLOWED_SCOPES = {"posture_full", "posture_framework"}

SHARES_FILE = "trust_shares.jsonl"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _gold(lake_dir: str | Path) -> Path:
    return Path(lake_dir) / "gold"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_share(
    lake_dir: str | Path,
    *,
    role: str,
    scope: str = "posture_full",
    expires_in_hours: int = 24,
    created_by: str = "console",
    framework_id: str | None = None,
) -> dict[str, Any]:
    """Issue a new share. Returns the raw token (only once) and the record."""
    if role not in ALLOWED_ROLES:
        raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
    if scope not in ALLOWED_SCOPES:
        raise ValueError(f"scope must be one of {sorted(ALLOWED_SCOPES)}")
    if expires_in_hours <= 0 or expires_in_hours > 24 * 90:
        raise ValueError("expires_in_hours must be between 1 and 2160 (90 days)")
    now = _utc_now()
    expires_at = now + timedelta(hours=expires_in_hours)
    token = "trust_" + secrets.token_urlsafe(24)
    share_id = secrets.token_urlsafe(8)
    record = {
        "share_id": share_id,
        "role": role,
        "scope": scope,
        "framework_id": framework_id,
        "expires_at": _iso(expires_at),
        "created_by": created_by,
        "created_at": _iso(now),
        "revoked_at": None,
        "token_sha256": _hash_token(token),
    }
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    with (gold / SHARES_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    return {**record, "token": token}


def list_shares(lake_dir: str | Path, *, include_revoked: bool = False) -> list[dict[str, Any]]:
    """Return current shares (latest record per share_id), optionally including revoked."""
    path = _gold(lake_dir) / SHARES_FILE
    if not path.is_file():
        return []
    latest: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = str(row.get("share_id") or "")
        if not sid:
            continue
        prev = latest.get(sid)
        if prev is None or str(row.get("created_at") or "") >= str(prev.get("created_at") or ""):
            latest[sid] = row
    rows = list(latest.values())
    if not include_revoked:
        rows = [r for r in rows if not r.get("revoked_at")]
    now = _iso(_utc_now())
    for row in rows:
        row["expired"] = bool(row.get("expires_at") and row["expires_at"] < now)
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return rows


def resolve_share(lake_dir: str | Path, token: str) -> dict[str, Any] | None:
    """Resolve a raw token to its live share record, or ``None``.

    Hashes the presented token and returns the matching share only if it is
    neither revoked nor expired. Returns ``None`` for any miss so the caller
    can answer a generic 404 without leaking whether the token was unknown,
    revoked, or simply past its expiry.
    """
    if not token:
        return None
    token_hash = _hash_token(token)
    now = _iso(_utc_now())
    for record in list_shares(lake_dir, include_revoked=False):
        if record.get("token_sha256") != token_hash:
            continue
        if record.get("revoked_at"):
            return None
        expires_at = record.get("expires_at")
        if expires_at and str(expires_at) < now:
            return None
        return record
    return None


def revoke_share(lake_dir: str | Path, share_id: str, *, actor: str = "console") -> dict[str, Any] | None:
    """Append a revocation record so the share can no longer be presented."""
    shares = list_shares(lake_dir, include_revoked=True)
    match = next((s for s in shares if s.get("share_id") == share_id), None)
    if match is None or match.get("revoked_at"):
        return match
    revoked = {
        **match,
        "revoked_at": _iso(_utc_now()),
        "revoked_by": actor,
    }
    with (_gold(lake_dir) / SHARES_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(revoked, separators=(",", ":")) + "\n")
    return revoked
