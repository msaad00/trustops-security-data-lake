"""Workflow (story) DAG + action library + persistence.

A workflow is a directed acyclic graph of typed actions that runs against
the lake. The library aims for Tines-grade UX: every node has a published
input/output schema, can be tested live with sample data, and the whole
DAG is versioned + persisted append-only.

Persistence
-----------
* ``gold/workflows.jsonl``     — append-only workflow versions; each line
  is a full snapshot (``workflow_id``, ``version``, ``nodes``, ``edges``,
  ``actor``, ``occurred_at``). The latest version per id is materialized
  on read.
* ``gold/workflow_runs.jsonl`` — append-only execution log; each line is
  one whole-DAG run with per-node results.

Action library (the registry is the extension point):

  trigger.evidence_changed     fires when new silver events land
  trigger.cron                 fires on a cron schedule (informational)
  check.evidence_exists        passes when N silver events match a filter
  check.control_pass           passes when a control_id's latest test is "pass"
  action.snapshot              freezes a point-in-time assessment snapshot
  action.assign_owner          appends a triage event with assignee + state
  action.webhook               POSTs to an allowlisted, SSRF-guarded URL

Egress safety
-------------
``action.webhook`` is the engine's first OUTBOUND action. Egress is
deny-by-default: a target host must match ``TRUSTOPS_WORKFLOW_EGRESS_ALLOWLIST``
(comma-separated ``host`` or ``host:port`` patterns) or the action refuses to
run. Every target is additionally SSRF-guarded — only ``http``/``https`` is
allowed and the *resolved* IP(s) must be public (private, loopback, link-local,
reserved and multicast ranges are rejected, as is ``localhost``). Secrets are
referenced as ``{{secret.NAME}}`` and resolved from ``TRUSTOPS_SECRET_<NAME>``
at run time; the resolved value is never written to the run log — the persisted
params keep the ``{{secret.NAME}}`` token.

Every action declares its input schema (the params the user fills in) and
its output schema (the keys downstream nodes can read), so the canvas can
validate edge wiring and the "Test action" button can render a form +
display the live result.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from security_lakehouse.assessment import write_assessment_snapshot
from security_lakehouse.io import read_jsonl
from security_lakehouse.tracking import append_event as append_triage_event

WORKFLOWS_FILE = "workflows.jsonl"
RUNS_FILE = "workflow_runs.jsonl"

_RUN_ACTORS = {"console", "scheduler", "api"}

# --- webhook egress safety -------------------------------------------------
EGRESS_ALLOWLIST_ENV = "TRUSTOPS_WORKFLOW_EGRESS_ALLOWLIST"
SECRET_ENV_PREFIX = "TRUSTOPS_SECRET_"
_WEBHOOK_TIMEOUT_SECONDS = 15
_WEBHOOK_BACKOFF_CAP_SECONDS = 2.0
_SECRET_RE = re.compile(r"\{\{\s*secret\.([A-Za-z0-9_]+)\s*\}\}")


# ---------------------------------------------------------------------------
# Action library
# ---------------------------------------------------------------------------


def _evidence_changed(_lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "trigger_kind": "evidence_changed",
        "since": params.get("since"),
        "matched": True,
    }


def _cron(_lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    return {"trigger_kind": "cron", "schedule": params.get("schedule") or "@hourly"}


def _check_evidence_exists(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    control_id = str(params.get("control_id") or "")
    minimum = int(params.get("minimum") or 1)
    silver = lake / "silver" / "normalized_events.jsonl"
    matched = 0
    if silver.is_file():
        for row in read_jsonl(silver):
            if control_id and control_id not in (row.get("control_ids") or []):
                continue
            matched += 1
    return {"matched_count": matched, "passed": matched >= minimum, "minimum": minimum}


def _check_control_pass(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    control_id = str(params.get("control_id") or "")
    tests = lake / "gold" / "control_tests.jsonl"
    if not tests.is_file():
        return {"control_id": control_id, "passed": False, "reason": "no control_tests.jsonl"}
    rows = [r for r in read_jsonl(tests) if r.get("control_id") == control_id]
    if not rows:
        return {"control_id": control_id, "passed": False, "reason": "control not found"}
    rows.sort(key=lambda r: str(r.get("evaluated_at") or ""), reverse=True)
    latest = rows[0]
    return {
        "control_id": control_id,
        "passed": latest.get("result") == "pass",
        "result": latest.get("result"),
        "confidence_score": latest.get("confidence_score"),
    }


def _action_snapshot(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    reason = str(params.get("reason") or "workflow_run")
    path = write_assessment_snapshot(lake, reason=reason)
    return {"snapshot_path": str(path), "reason": reason}


def _action_assign_owner(lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    violation_id = str(params.get("violation_id") or "")
    assignee = str(params.get("assignee") or "")
    if not violation_id:
        raise ValueError("violation_id is required")
    record = append_triage_event(
        lake,
        violation_id=violation_id,
        actor=str(params.get("actor") or "workflow"),
        state=str(params.get("state") or "triaged"),
        assignee=assignee or None,
        due_at=params.get("due_at"),
        note=params.get("note") or "auto-assigned by workflow",
    )
    return {"violation_id": violation_id, "assignee": assignee, "tracking_id": record["tracking_id"]}


# ---------------------------------------------------------------------------
# action.webhook — first OUTBOUND/egress action (deny-by-default + SSRF guard)
# ---------------------------------------------------------------------------


def _webhook_backoff_sleep(seconds: float) -> None:
    """Indirection point so tests can monkeypatch the retry sleep to a no-op."""
    time.sleep(seconds)


def _load_egress_allowlist() -> set[str]:
    """Parse ``TRUSTOPS_WORKFLOW_EGRESS_ALLOWLIST`` into normalized host[:port] entries.

    An empty/unset env means egress is disabled (deny-by-default); the caller
    treats an empty set as "deny all".
    """
    raw = os.environ.get(EGRESS_ALLOWLIST_ENV, "")
    entries: set[str] = set()
    for chunk in raw.split(","):
        entry = chunk.strip().lower()
        if entry:
            entries.add(entry)
    return entries


def _host_is_allowlisted(host: str, port: int, allowlist: set[str]) -> bool:
    """A target matches if its bare host or its explicit ``host:port`` is listed."""
    host = host.lower()
    if host in allowlist:
        return True
    return f"{host}:{port}" in allowlist


def _assert_resolved_ip_is_public(host: str) -> list[str]:
    """Resolve ``host`` and reject any address in a non-public range (SSRF guard).

    The private/loopback/link-local/reserved/multicast check runs on the
    *resolved* address(es), not just the hostname string, so a public-looking
    name that resolves to ``127.0.0.1`` (DNS rebinding / internal split-horizon)
    is still blocked. Returns the resolved addresses on success.
    """
    if host.lower() == "localhost":
        raise ValueError("webhook target 'localhost' is not allowed")
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise ValueError(f"webhook target host {host!r} did not resolve: {exc}") from exc
    addresses: list[str] = []
    for info in infos:
        sockaddr = info[4]
        addresses.append(str(sockaddr[0]))
    if not addresses:
        raise ValueError(f"webhook target host {host!r} did not resolve to any address")
    for raw_ip in addresses:
        # Strip any IPv6 scope id (e.g. fe80::1%eth0) before parsing.
        ip = ipaddress.ip_address(raw_ip.split("%", 1)[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(f"webhook target resolves to non-public address {raw_ip} (SSRF blocked)")
    return addresses


def _resolve_secrets(value: Any) -> Any:
    """Replace ``{{secret.NAME}}`` tokens from ``TRUSTOPS_SECRET_<NAME>`` env.

    Applied to the request actually sent on the wire. The caller must NOT feed
    the resolved result back into anything that is persisted — the run log keeps
    the pre-resolution token form so the secret value never lands on disk.
    """
    if isinstance(value, str):

        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            env_key = f"{SECRET_ENV_PREFIX}{name}"
            secret = os.environ.get(env_key)
            if secret is None:
                raise ValueError(f"secret {name!r} is not set (expected env {env_key})")
            return secret

        return _SECRET_RE.sub(repl, value)
    if isinstance(value, list):
        return [_resolve_secrets(item) for item in value]
    if isinstance(value, dict):
        return {k: _resolve_secrets(v) for k, v in value.items()}
    return value


def _redact_secret_tokens(value: Any) -> Any:
    """Best-effort: rewrite any ``{{secret.NAME}}`` token to ``[secret]``.

    Defense in depth for output echoing — even though secrets are only resolved
    on the outbound copy, this guards against a token (and never the value) ever
    being surfaced verbatim in a snippet that mirrors request content.
    """
    if isinstance(value, str):
        return _SECRET_RE.sub("[secret]", value)
    if isinstance(value, list):
        return [_redact_secret_tokens(item) for item in value]
    if isinstance(value, dict):
        return {k: _redact_secret_tokens(v) for k, v in value.items()}
    return value


def _webhook_idempotency_key(params: dict[str, Any]) -> str:
    """Stable per-node-run key so retries/replays of identical params don't double-fire.

    Derived from the *templated* (pre-secret-resolution) params, so the key
    never depends on — or leaks — a secret value, yet stays constant across the
    retry loop of a single run.
    """
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _action_webhook(_lake: Path, params: dict[str, Any]) -> dict[str, Any]:
    """POST to an allowlisted, SSRF-guarded URL with retry + idempotency.

    ``params`` arrives already templated for ``{{node.output.*}}`` (resolved by
    ``run_workflow``) but still carrying ``{{secret.NAME}}`` tokens — secrets are
    resolved here, on the outbound request only, so the persisted node params and
    this output keep the token form.
    """
    url_template = params.get("url")
    if not url_template or not isinstance(url_template, str):
        raise ValueError("webhook 'url' is required")

    # --- allowlist + SSRF guard run on the *templated* url (pre-secret) so a
    # secret can never smuggle the request past the gate. ---
    parsed = urlsplit(url_template)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"webhook url scheme {parsed.scheme!r} is not allowed (http/https only)")
    host = parsed.hostname
    if not host:
        raise ValueError("webhook url has no host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    allowlist = _load_egress_allowlist()
    if not allowlist:
        raise ValueError("workflow egress is disabled; set TRUSTOPS_WORKFLOW_EGRESS_ALLOWLIST")
    if not _host_is_allowlisted(host, port, allowlist):
        raise ValueError(f"webhook target host {host!r} is not in the egress allowlist")
    _assert_resolved_ip_is_public(host)

    try:
        max_retries = int(params.get("max_retries", 2))
    except (TypeError, ValueError):
        max_retries = 2
    max_retries = max(0, max_retries)

    idempotency_key = _webhook_idempotency_key(params)

    # Resolve secrets ONLY on the outbound copy. raw_* stays token-form.
    url = str(_resolve_secrets(url_template))
    raw_body = params.get("body")
    body_value = _resolve_secrets(raw_body) if raw_body is not None else None
    if body_value is None:
        data = None
    elif isinstance(body_value, str):
        data = body_value.encode("utf-8")
    else:
        data = json.dumps(body_value, separators=(",", ":")).encode("utf-8")

    header_template = params.get("headers") or {}
    if not isinstance(header_template, dict):
        raise ValueError("webhook 'headers' must be an object")
    headers: dict[str, str] = {str(k): str(_resolve_secrets(v)) for k, v in header_template.items()}
    headers.setdefault("Idempotency-Key", idempotency_key)
    if data is not None and not any(k.lower() == "content-type" for k in headers):
        headers["Content-Type"] = "application/json"

    last_error: str | None = None
    status_code = 0
    response_snippet = ""
    ok = False
    attempts = 0
    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")  # noqa: S310 (scheme + allowlist + SSRF guarded above)
        try:
            with urllib.request.urlopen(request, timeout=_WEBHOOK_TIMEOUT_SECONDS) as resp:  # noqa: S310
                status_code = int(getattr(resp, "status", 0) or 0)
                payload = resp.read(2048)
                response_snippet = payload.decode("utf-8", errors="replace")[:500]
                ok = 200 <= status_code < 300
                last_error = None
                break
        except urllib.error.HTTPError as exc:
            status_code = int(exc.code)
            try:
                response_snippet = exc.read(2048).decode("utf-8", errors="replace")[:500]
            except Exception:  # noqa: BLE001 — snippet is best-effort
                response_snippet = ""
            ok = False
            if 400 <= status_code < 500:
                # 4xx is a client error — not retryable.
                last_error = None
                break
            last_error = f"HTTP {status_code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            status_code = 0
            ok = False
        if attempt < max_retries:
            sleep_for = min(_WEBHOOK_BACKOFF_CAP_SECONDS, 0.1 * (2**attempt))
            _webhook_backoff_sleep(sleep_for)

    return {
        "status_code": status_code,
        "ok": ok,
        "response_snippet": _redact_secret_tokens(response_snippet),
        "attempts": attempts,
        "idempotency_key": idempotency_key,
        "error": last_error,
    }


ACTION_LIBRARY: dict[str, dict[str, Any]] = {
    "trigger.evidence_changed": {
        "kind": "trigger",
        "label": "Evidence changed",
        "description": "Fires when new silver-layer evidence lands in the lake.",
        "input_schema": {"since": {"type": "string", "label": "Since (ISO 8601)", "optional": True}},
        "output_schema": {"trigger_kind": "string", "since": "string", "matched": "boolean"},
        "handler": _evidence_changed,
    },
    "trigger.cron": {
        "kind": "trigger",
        "label": "Cron schedule",
        "description": "Fires on a cron schedule (canvas-only; the runner is not wired yet).",
        "input_schema": {"schedule": {"type": "string", "label": "Cron expression", "default": "@hourly"}},
        "output_schema": {"trigger_kind": "string", "schedule": "string"},
        "handler": _cron,
    },
    "check.evidence_exists": {
        "kind": "check",
        "label": "Evidence exists",
        "description": "Passes when at least N silver-layer events match the given control_id.",
        "input_schema": {
            "control_id": {"type": "string", "label": "Control id", "required": True},
            "minimum": {"type": "number", "label": "Minimum count", "default": 1},
        },
        "output_schema": {"matched_count": "number", "passed": "boolean", "minimum": "number"},
        "handler": _check_evidence_exists,
    },
    "check.control_pass": {
        "kind": "check",
        "label": "Control passes",
        "description": "Passes when the latest control test for this control_id is 'pass'.",
        "input_schema": {"control_id": {"type": "string", "label": "Control id", "required": True}},
        "output_schema": {
            "control_id": "string",
            "passed": "boolean",
            "result": "string",
            "confidence_score": "number",
        },
        "handler": _check_control_pass,
    },
    "action.snapshot": {
        "kind": "action",
        "label": "Freeze snapshot",
        "description": "Writes a point-in-time assessment snapshot to gold/snapshots/.",
        "input_schema": {"reason": {"type": "string", "label": "Reason", "default": "workflow_run"}},
        "output_schema": {"snapshot_path": "string", "reason": "string"},
        "handler": _action_snapshot,
    },
    "action.assign_owner": {
        "kind": "action",
        "label": "Assign owner",
        "description": "Appends a triage event with an assignee for a violation_id.",
        "input_schema": {
            "violation_id": {"type": "string", "label": "Violation id", "required": True},
            "assignee": {"type": "string", "label": "Assignee", "required": True},
            "state": {"type": "string", "label": "State", "default": "triaged"},
            "note": {"type": "string", "label": "Note", "optional": True},
            "due_at": {"type": "string", "label": "Due (ISO 8601)", "optional": True},
        },
        "output_schema": {"violation_id": "string", "assignee": "string", "tracking_id": "string"},
        "handler": _action_assign_owner,
    },
    "action.webhook": {
        "kind": "action",
        "label": "Send webhook",
        "description": (
            "POSTs to an allowlisted, SSRF-guarded URL. Egress is deny-by-default "
            "(TRUSTOPS_WORKFLOW_EGRESS_ALLOWLIST); {{secret.NAME}} tokens resolve "
            "from TRUSTOPS_SECRET_<NAME> at run time and are never persisted."
        ),
        "input_schema": {
            "url": {"type": "string", "label": "URL", "required": True},
            "body": {"type": "string", "label": "Body (JSON or text)", "optional": True},
            "headers": {"type": "object", "label": "Headers", "optional": True},
            "max_retries": {"type": "number", "label": "Max retries", "default": 2},
        },
        "output_schema": {
            "status_code": "number",
            "ok": "boolean",
            "response_snippet": "string",
        },
        "handler": _action_webhook,
    },
}


def action_catalog() -> list[dict[str, Any]]:
    """Return the action library minus handler refs (the React canvas reads this)."""
    return [
        {
            "node_type": node_type,
            "kind": spec["kind"],
            "label": spec["label"],
            "description": spec["description"],
            "input_schema": spec["input_schema"],
            "output_schema": spec["output_schema"],
        }
        for node_type, spec in ACTION_LIBRARY.items()
    ]


def run_action(
    lake_dir: str | Path,
    *,
    node_type: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a single action node against the lake and return its output."""
    spec = ACTION_LIBRARY.get(node_type)
    if spec is None:
        raise ValueError(f"unknown node_type {node_type!r}")
    handler = spec["handler"]
    return handler(Path(lake_dir), params or {})


# ---------------------------------------------------------------------------
# Workflow persistence
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _gold(lake_dir: str | Path) -> Path:
    return Path(lake_dir) / "gold"


def _read_log(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _slugify(text: str) -> str:
    clean = "".join(c if c.isalnum() or c in "-_" else "-" for c in text.lower())
    while "--" in clean:
        clean = clean.replace("--", "-")
    return clean.strip("-") or "workflow"


def _validate_workflow_graph(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    """Reject structurally invalid workflows before they are persisted.

    Guards against unknown node types, missing/duplicate node ids, edges that
    reference non-existent nodes, and cycles. A saved workflow is therefore
    always a runnable DAG over known actions, rather than failing opaquely (or
    running in a nondeterministic order) at execution time.
    """
    if not isinstance(edges, list):
        raise ValueError("workflow edges must be a list")
    ids: list[str] = []
    for node in nodes:
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            raise ValueError("every workflow node requires a non-empty 'id'")
        node_type = str(node.get("node_type") or "")
        if node_type not in ACTION_LIBRARY:
            raise ValueError(f"unknown node_type {node_type!r} for node {node_id!r}")
        ids.append(node_id)
    id_set = set(ids)
    if len(id_set) != len(ids):
        duplicates = sorted({nid for nid in ids if ids.count(nid) > 1})
        raise ValueError(f"duplicate node ids: {duplicates}")

    incoming: dict[str, list[str]] = {nid: [] for nid in id_set}
    outgoing: dict[str, list[str]] = {nid: [] for nid in id_set}
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in id_set:
            raise ValueError(f"edge source {source!r} is not a node id")
        if target not in id_set:
            raise ValueError(f"edge target {target!r} is not a node id")
        incoming[target].append(source)
        outgoing[source].append(target)

    # Kahn's algorithm: if any node never reaches in-degree 0, a cycle exists.
    indegree = {nid: len(parents) for nid, parents in incoming.items()}
    ready = [nid for nid, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        nid = ready.pop()
        visited += 1
        for child in outgoing[nid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if visited != len(id_set):
        raise ValueError("workflow graph must be acyclic (a cycle was detected)")


def save_workflow(
    lake_dir: str | Path,
    *,
    workflow_id: str | None,
    name: str,
    description: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    actor: str = "console",
) -> dict[str, Any]:
    """Append a new version of a workflow (auto-generates workflow_id if absent)."""
    if not name:
        raise ValueError("workflow name is required")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("workflow must declare at least one node")
    _validate_workflow_graph(nodes, edges)
    workflow_id = workflow_id or _slugify(name)
    existing = list_workflows(lake_dir)
    versions = [w for w in existing if w["workflow_id"] == workflow_id]
    version = (max(int(v.get("version") or 0) for v in versions) + 1) if versions else 1
    record = {
        "workflow_id": workflow_id,
        "version": version,
        "name": name,
        "description": description,
        "nodes": nodes,
        "edges": edges,
        "actor": actor,
        "occurred_at": _utc_now_iso(),
        "hash": hashlib.sha256(
            json.dumps({"nodes": nodes, "edges": edges}, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16],
    }
    gold = _gold(lake_dir)
    gold.mkdir(parents=True, exist_ok=True)
    with (gold / WORKFLOWS_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def list_workflows(lake_dir: str | Path) -> list[dict[str, Any]]:
    """Return the latest version per workflow_id, newest-saved first."""
    rows = _read_log(_gold(lake_dir) / WORKFLOWS_FILE)
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        wid = str(row.get("workflow_id") or "")
        if not wid:
            continue
        prev = latest.get(wid)
        if prev is None or int(row.get("version") or 0) > int(prev.get("version") or 0):
            latest[wid] = row
    return sorted(latest.values(), key=lambda r: str(r.get("occurred_at") or ""), reverse=True)


def get_workflow(lake_dir: str | Path, workflow_id: str) -> dict[str, Any] | None:
    for w in list_workflows(lake_dir):
        if w["workflow_id"] == workflow_id:
            return w
    return None


_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\.output\.([A-Za-z0-9_]+)\s*\}\}")


def _substitute_variables(
    params: dict[str, Any],
    outputs_by_node: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Replace ``{{nodeId.output.field}}`` references in string params."""

    def resolve(value: Any) -> Any:
        if isinstance(value, str):

            def repl(match: re.Match[str]) -> str:
                node_id = match.group(1)
                field = match.group(2)
                source = outputs_by_node.get(node_id)
                if not source:
                    return match.group(0)
                replacement = source.get(field)
                if replacement is None:
                    return ""
                return str(replacement)

            return _VAR_RE.sub(repl, value)
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, dict):
            return {k: resolve(v) for k, v in value.items()}
        return value

    return {k: resolve(v) for k, v in params.items()}


def _edge_allows(edge: dict[str, Any], parent_result: dict[str, Any] | None) -> bool:
    """Return True if `edge` should fire given the parent node's run result."""
    condition = str(edge.get("condition") or "always").lower()
    if condition == "always":
        return True
    if parent_result is None or parent_result.get("result") != "ok":
        return False
    output = parent_result.get("output") or {}
    passed = bool(output.get("passed"))
    if condition == "passed":
        return passed
    if condition == "failed":
        return not passed
    return True


def run_workflow(
    lake_dir: str | Path,
    *,
    workflow_id: str,
    actor: str = "console",
) -> dict[str, Any]:
    """Execute every node in a workflow (topological order) and persist the run.

    Variable references ``{{nodeId.output.field}}`` in params are substituted
    from upstream node outputs before each action runs. Edges with
    ``condition: "passed"|"failed"`` gate the target node based on the parent
    check's ``output.passed`` boolean.
    """
    if actor not in _RUN_ACTORS:
        actor = "console"
    workflow = get_workflow(lake_dir, workflow_id)
    if workflow is None:
        raise ValueError(f"unknown workflow_id {workflow_id!r}")
    nodes_by_id = {str(n.get("id")): n for n in workflow["nodes"]}
    edges: list[dict[str, Any]] = list(workflow.get("edges") or [])
    parents: dict[str, list[dict[str, Any]]] = {nid: [] for nid in nodes_by_id}
    incoming: dict[str, list[str]] = {nid: [] for nid in nodes_by_id}
    for edge in edges:
        src = str(edge.get("source"))
        dst = str(edge.get("target"))
        if dst in incoming:
            incoming[dst].append(src)
            parents[dst].append(edge)
    order = _topo_sort(nodes_by_id, incoming)
    started_at = _utc_now_iso()
    node_results: list[dict[str, Any]] = []
    outputs_by_node: dict[str, dict[str, Any]] = {}
    results_by_node: dict[str, dict[str, Any]] = {}
    # Per-branch failure isolation: a node that errors (or is skipped because an
    # upstream node never completed) only blocks its *downstream descendants*.
    # Independent parallel branches keep running, instead of aborting the whole
    # DAG on the first error.
    any_failed = False
    failed_nodes: set[str] = set()
    blocked: set[str] = set()
    for node_id in order:
        node = nodes_by_id[node_id]
        node_type = str(node.get("node_type") or "")
        raw_params = node.get("params") or {}
        # Branch isolation gate (runs before the edge-condition gate): if any
        # parent errored or was itself blocked, this node cannot run. Skip it
        # and mark it blocked so its own descendants skip too.
        skip_reason: str | None = None
        for edge in parents.get(node_id, []):
            parent_id = str(edge.get("source"))
            if parent_id in failed_nodes or parent_id in blocked:
                skip_reason = f"upstream node {parent_id} did not complete"
                blocked.add(node_id)
                break
        # Gate on incoming edge conditions: skip the node if *any* parent
        # edge declines (failed condition with the parent's `passed=true`,
        # or vice versa). This mirrors how Tines edges flow conditionally.
        if skip_reason is None:
            for edge in parents.get(node_id, []):
                parent_id = str(edge.get("source"))
                parent_result = results_by_node.get(parent_id)
                if not _edge_allows(edge, parent_result):
                    condition = str(edge.get("condition") or "always")
                    skip_reason = f"edge from {parent_id} declined (condition={condition})"
                    break
        if skip_reason:
            entry = {
                "node_id": node_id,
                "node_type": node_type,
                "params": raw_params,
                "result": "skipped",
                "reason": skip_reason,
            }
            node_results.append(entry)
            results_by_node[node_id] = entry
            continue
        params = _substitute_variables(raw_params, outputs_by_node)
        result_entry: dict[str, Any] = {
            "node_id": node_id,
            "node_type": node_type,
            "params": params,
        }
        try:
            output = run_action(lake_dir, node_type=node_type, params=params)
            result_entry["result"] = "ok"
            result_entry["output"] = output
            outputs_by_node[node_id] = output
        except Exception as exc:  # surface every failure in the run log
            any_failed = True
            failed_nodes.add(node_id)
            result_entry["result"] = "error"
            result_entry["error"] = str(exc)
        node_results.append(result_entry)
        results_by_node[node_id] = result_entry
        # No break: a node failure only blocks its descendants (handled by the
        # branch-isolation gate above); independent branches keep running.
    run = {
        "workflow_id": workflow_id,
        "workflow_version": workflow["version"],
        "actor": actor,
        "result": "error" if any_failed else "ok",
        "started_at": started_at,
        "finished_at": _utc_now_iso(),
        "node_results": node_results,
    }
    with (_gold(lake_dir) / RUNS_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(run, separators=(",", ":")) + "\n")
    return run


def list_runs(lake_dir: str | Path, workflow_id: str | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = _read_log(_gold(lake_dir) / RUNS_FILE)
    if workflow_id:
        rows = [r for r in rows if r.get("workflow_id") == workflow_id]
    rows.sort(key=lambda r: str(r.get("started_at") or ""), reverse=True)
    return rows[:limit]


def _topo_sort(nodes_by_id: dict[str, dict], incoming: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm. Cycles fall back to insertion order so the run still attempts."""
    indeg = {nid: len(parents) for nid, parents in incoming.items()}
    ready = [nid for nid, n in indeg.items() if n == 0]
    order: list[str] = []
    seen: set[str] = set()
    # Outgoing index
    outgoing: dict[str, list[str]] = {nid: [] for nid in nodes_by_id}
    for child, parents in incoming.items():
        for parent in parents:
            if parent in outgoing:
                outgoing[parent].append(child)
    while ready:
        nid = ready.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        order.append(nid)
        for child in outgoing.get(nid, []):
            indeg[child] = max(0, indeg[child] - 1)
            if indeg[child] == 0:
                ready.append(child)
    # Append any cycle survivors so the workflow still runs partially.
    for nid in nodes_by_id:
        if nid not in seen:
            order.append(nid)
    return order
