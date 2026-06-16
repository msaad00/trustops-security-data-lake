"""Re-fetch official framework sources, recompute sha256, advance pulled_at.

Runs as ``security-lakehouse frameworks sync`` (CLI) and on a cron via
``.github/workflows/framework-sync.yml``. The job is intentionally append-only
in spirit: it mutates ``frameworks/registry.json`` in place but only the
``source_sha256`` + ``pulled_at`` fields, and only when the upstream body has
changed (sha differs from what's in the registry).

When run with ``--open-pr`` and inside GitHub Actions, the workflow that calls
this CLI opens a pull request with the diff so a human reviewer ratifies the
drift before merging.

Network access is opt-in (``--allow-network``). Offline runs only mark every
framework as "skipped — network disabled" so unit tests don't make HTTP calls.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import DEFAULT_FRAMEWORK_REGISTRY
from security_lakehouse.io import append_jsonl

USER_AGENT = "trustops-framework-sync/1.0"
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class SyncResult:
    framework_id: str
    state: str  # "updated" | "unchanged" | "skipped" | "error"
    old_sha: str | None
    new_sha: str | None
    pulled_at: str | None
    reason: str | None


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _fetch(url: str, *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def sync_frameworks(
    registry_path: str | Path | None = None,
    *,
    allow_network: bool = False,
    fetcher: Any | None = None,
    history_path: str | Path | None = None,
    refresh_bundle_lock: bool = True,
) -> list[SyncResult]:
    """Sync every framework in the registry. Returns one SyncResult per framework.

    ``fetcher`` is an optional callable taking (url) -> bytes; tests inject a
    fake fetcher to avoid network. When ``allow_network`` is False and no
    fetcher is provided, every framework is marked ``skipped``.
    """
    path = Path(registry_path or DEFAULT_FRAMEWORK_REGISTRY)
    payload = json.loads(path.read_text(encoding="utf-8"))
    frameworks = payload.get("frameworks") or []
    if not isinstance(frameworks, list):
        raise ValueError("registry must contain a frameworks list")

    results: list[SyncResult] = []
    dirty = False
    for framework in frameworks:
        framework_id = str(framework.get("framework_id") or "")
        url = str(framework.get("official_source_url") or "")
        old_sha = framework.get("source_sha256")
        if not framework_id or not url:
            results.append(
                SyncResult(
                    framework_id=framework_id or "<unknown>",
                    state="error",
                    old_sha=old_sha,
                    new_sha=None,
                    pulled_at=framework.get("pulled_at"),
                    reason="registry entry missing framework_id or official_source_url",
                )
            )
            continue
        if fetcher is None and not allow_network:
            results.append(
                SyncResult(
                    framework_id=framework_id,
                    state="skipped",
                    old_sha=old_sha,
                    new_sha=None,
                    pulled_at=framework.get("pulled_at"),
                    reason="network disabled (--allow-network not set)",
                )
            )
            continue
        try:
            body = (fetcher or _fetch)(url)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            results.append(
                SyncResult(
                    framework_id=framework_id,
                    state="error",
                    old_sha=old_sha,
                    new_sha=None,
                    pulled_at=framework.get("pulled_at"),
                    reason=f"fetch failed: {exc.__class__.__name__}: {exc}",
                )
            )
            continue
        new_sha = hashlib.sha256(body).hexdigest()
        pulled_at = _utc_iso()
        framework["pulled_at"] = pulled_at
        framework["source_sha256"] = new_sha
        state = "unchanged" if new_sha == old_sha else "updated"
        if state == "updated":
            dirty = True
            # Append-only record of the source drift so the history of *what the
            # upstream said when* survives even before a human assigns a new
            # version label in the registry. History sits next to the registry
            # being synced so a tmp registry never writes to the repo's ledger.
            append_jsonl(
                Path(history_path) if history_path else path.parent / "history.jsonl",
                {
                    "framework_id": framework_id,
                    "version": framework.get("version"),
                    "old_source_sha256": old_sha,
                    "new_source_sha256": new_sha,
                    "official_source_url": url,
                    "pulled_at": pulled_at,
                },
            )
        results.append(
            SyncResult(
                framework_id=framework_id,
                state=state,
                old_sha=old_sha,
                new_sha=new_sha,
                pulled_at=pulled_at,
                reason=None,
            )
        )

    # Always rewrite (atomic) so even unchanged-but-touched pulled_at lands.
    if any(r.state in {"updated", "unchanged"} for r in results):
        path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    # Re-lock the catalog bundle so source drift is reflected in the audit pin.
    # Only for the real default registry — the bundle spans repo-global controls
    # + crosswalk, so re-locking on a caller-supplied (e.g. tmp) registry would
    # mix paths and clobber the committed lockfile.
    if dirty and refresh_bundle_lock and registry_path is None:
        try:
            from security_lakehouse.catalog_versions import write_bundle_lock

            write_bundle_lock()
        except (OSError, ValueError):
            pass
    return results
