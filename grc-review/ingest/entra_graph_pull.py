#!/usr/bin/env python3
"""Pull Microsoft Entra users via Graph delta → Azure Blob for Snowpipe.

Features:
  - /users/delta incremental sync (stores deltaLink watermark locally or in Snowflake)
  - 429 Retry-After + exponential backoff
  - ingest_batch_id per run; skips blob write when delta is empty
  - JSON array file shaped for Snowpipe STRIP_OUTER_ARRAY

Usage:
  export AZURE_TENANT_ID=...
  export AZURE_CLIENT_ID=...
  export AZURE_CLIENT_SECRET=...
  export AZURE_STORAGE_CONNECTION_STRING=...
  export AZURE_STORAGE_CONTAINER=grc-review
  python entra_graph_pull.py

No LLM required. Suitable as Harvey scripting interview reference.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
DEFAULT_SCOPES = "https://graph.microsoft.com/.default"
WATERMARK_FILE = Path(__file__).resolve().parent / ".entra_delta_watermark.json"
USER_SELECT = "id,userPrincipalName,mail,accountEnabled,employeeId,displayName"


def utc_batch_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def log(msg: str) -> None:
    print(f"[{datetime.now(UTC).isoformat()}] {msg}", flush=True)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def get_token() -> str:
    tenant = env("AZURE_TENANT_ID")
    client_id = env("AZURE_CLIENT_ID")
    client_secret = env("AZURE_CLIENT_SECRET")
    if not all([tenant, client_id, client_secret]):
        raise SystemExit("Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")

    body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": DEFAULT_SCOPES,
            "grant_type": "client_credentials",
        }
    ).encode()
    req = urllib.request.Request(
        TOKEN_URL.format(tenant=tenant),
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"token response missing access_token: {payload}")
    return str(token)


def read_watermark() -> str | None:
    if WATERMARK_FILE.is_file():
        data = json.loads(WATERMARK_FILE.read_text())
        return data.get("delta_link")
    return None


def write_watermark(delta_link: str) -> None:
    WATERMARK_FILE.write_text(
        json.dumps({"delta_link": delta_link, "updated_at": datetime.now(UTC).isoformat()}, indent=2)
    )


def request_json(
    url: str,
    token: str,
    *,
    max_retries: int = 6,
) -> dict[str, Any]:
    attempt = 0
    while True:
        attempt += 1
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt <= max_retries:
                retry_after = int(exc.headers.get("Retry-After", "0") or 0)
                sleep_s = retry_after or min(2**attempt + random.random(), 60)
                log(f"429 rate limited — sleeping {sleep_s:.1f}s (attempt {attempt})")
                time.sleep(sleep_s)
                continue
            if exc.code in {500, 502, 503, 504} and attempt <= max_retries:
                sleep_s = min(2**attempt + random.random(), 60)
                log(f"HTTP {exc.code} — retry in {sleep_s:.1f}s")
                time.sleep(sleep_s)
                continue
            body = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"Graph HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            if attempt <= max_retries:
                sleep_s = min(2**attempt + random.random(), 30)
                log(f"network error {exc} — retry in {sleep_s:.1f}s")
                time.sleep(sleep_s)
                continue
            raise


def fetch_delta_users(token: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return (records, new_delta_link). Each record has source_operation upsert|delete."""
    delta_link = read_watermark()
    if delta_link:
        url = delta_link
        log(f"Resuming delta: {delta_link[:80]}...")
    else:
        qs = urllib.parse.urlencode({"$select": USER_SELECT})
        url = f"{GRAPH_BASE}/users/delta?{qs}"
        log("Starting initial delta (full seed)")

    records: list[dict[str, Any]] = []
    new_delta_link: str | None = None

    while url:
        page = request_json(url, token)
        for item in page.get("value") or []:
            if not isinstance(item, dict):
                continue
            op = "delete" if "@removed" in item else "upsert"
            records.append(
                {
                    "id": item.get("id"),
                    "userPrincipalName": item.get("userPrincipalName"),
                    "mail": item.get("mail"),
                    "accountEnabled": item.get("accountEnabled"),
                    "employeeId": item.get("employeeId"),
                    "displayName": item.get("displayName"),
                    "source_operation": op,
                }
            )
        url = page.get("@odata.nextLink")
        if page.get("@odata.deltaLink"):
            new_delta_link = str(page["@odata.deltaLink"])

    return records, new_delta_link


def upload_blob(batch_id: str, records: list[dict[str, Any]]) -> str:
    conn = env("AZURE_STORAGE_CONNECTION_STRING")
    container = env("AZURE_STORAGE_CONTAINER", "grc-review")
    if not conn:
        raise SystemExit("Set AZURE_STORAGE_CONNECTION_STRING")

    try:
        from azure.storage.blob import BlobServiceClient  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit("pip install azure-storage-blob") from exc

    ingest_time = datetime.now(UTC).isoformat()
    for row in records:
        row["ingest_time"] = ingest_time
        row["ingest_batch_id"] = batch_id

    blob_path = f"entra/ingest_batch_id={batch_id}/part-000.json"
    payload = json.dumps(records, separators=(",", ":")).encode()

    client = BlobServiceClient.from_connection_string(conn)
    blob = client.get_blob_client(container=container, blob=blob_path)
    blob.upload_blob(payload, overwrite=False)
    log(f"Uploaded {len(records)} records → {container}/{blob_path} ({len(payload)} bytes)")
    return blob_path


def write_jsonl_local(batch_id: str, records: list[dict[str, Any]], out_dir: Path) -> Path:
    """Offline/demo mode without Azure Blob."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ingest_time = datetime.now(UTC).isoformat()
    path = out_dir / f"entra_{batch_id}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in records:
            row["ingest_time"] = ingest_time
            row["ingest_batch_id"] = batch_id
            fh.write(json.dumps(row) + "\n")
    log(f"Wrote {len(records)} records → {path}")
    return path


def main() -> int:
    batch_id = utc_batch_id()
    token = get_token()
    records, new_delta_link = fetch_delta_users(token)

    upserts = sum(1 for r in records if r.get("source_operation") == "upsert")
    deletes = sum(1 for r in records if r.get("source_operation") == "delete")
    log(f"Delta result: {upserts} upserts, {deletes} deletes, batch={batch_id}")

    if not records:
        log("No changes — skipping blob write (Snowpipe/dbt have nothing new to process)")
        return 0

    if new_delta_link:
        write_watermark(new_delta_link)

    dry_run = env("DRY_RUN", "").lower() in {"1", "true", "yes"}
    if dry_run:
        write_jsonl_local(batch_id, records, Path("build/ingest"))
        return 0

    if env("AZURE_STORAGE_CONNECTION_STRING"):
        upload_blob(batch_id, records)
    else:
        write_jsonl_local(batch_id, records, Path("build/ingest"))
        log("No AZURE_STORAGE_CONNECTION_STRING — wrote local JSONL only")

    fingerprint = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()[:16]
    log(f"Batch fingerprint: {fingerprint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
