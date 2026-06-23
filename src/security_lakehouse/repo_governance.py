"""Authenticated repository governance evidence collector.

The public repo audit records what can be seen without credentials. This module
collects private/org-only governance signals when a GitHub App installation
token or fixture is available and emits the same raw evidence shape.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.io import read_json, write_jsonl
from security_lakehouse.models import utc_iso
from security_lakehouse.repo_audit import RepoSpec, parse_repo_spec

CONTROL_MAP = {
    "branch_protection": ["SOC2-CC6.1", "ISO27001-A.5.15", "PCI-DSS-7"],
    "collaborators": ["SOC2-CC6.1", "ISO27001-A.5.15"],
    "teams": ["SOC2-CC6.1", "ISO27001-A.5.15"],
    "workflow_permissions": ["SOC2-CC7.2", "ISO27001-A.8.16"],
    "security_settings": ["SOC2-CC7.2", "PCI-DSS-11", "GDPR-Art.32"],
}

READ_ONLY_SCOPES = ["metadata:read", "contents:read", "administration:read", "security_events:read"]


class GitHubGovernanceClient:
    def __init__(self, owner: str, repo: str, *, token: str) -> None:
        self.spec = RepoSpec(owner=owner, repo=repo)
        self.token = token

    def repo(self) -> dict[str, Any]:
        return self._json(f"https://api.github.com/repos/{self.spec.slug}")

    def branch_protection(self, branch: str) -> dict[str, Any]:
        return self._json(f"https://api.github.com/repos/{self.spec.slug}/branches/{branch}/protection")

    def collaborators(self) -> list[dict[str, Any]]:
        return self._json_list(f"https://api.github.com/repos/{self.spec.slug}/collaborators?per_page=100")

    def teams(self) -> list[dict[str, Any]]:
        return self._json_list(f"https://api.github.com/repos/{self.spec.slug}/teams?per_page=100")

    def workflow_permissions(self) -> dict[str, Any]:
        return self._json(f"https://api.github.com/repos/{self.spec.slug}/actions/permissions/workflow")

    def vulnerability_alerts(self) -> dict[str, Any]:
        return self._json(f"https://api.github.com/repos/{self.spec.slug}/vulnerability-alerts")

    def _json(self, url: str) -> dict[str, Any]:
        payload = self._request(url)
        if isinstance(payload, dict):
            return payload
        raise ValueError(f"GitHub returned non-object JSON for {url}")

    def _json_list(self, url: str) -> list[dict[str, Any]]:
        payload = self._request(url)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        raise ValueError(f"GitHub returned non-list JSON for {url}")

    def _request(self, url: str) -> object:
        request = urllib.request.Request(
            url,
            headers={
                "accept": "application/vnd.github+json",
                "authorization": f"Bearer {self.token}",
                "user-agent": "trustops-security-data-lake",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as resp:  # noqa: S310
            if resp.status == 204:
                return {"enabled": True}
            return json.loads(resp.read().decode("utf-8"))


class FixtureGovernanceClient:
    def __init__(self, fixture_dir: str | Path) -> None:
        self.fixture = Path(fixture_dir)

    def repo(self) -> dict[str, Any]:
        return read_json(self.fixture / "repo.json")

    def branch_protection(self, _branch: str) -> dict[str, Any]:
        return self._read("branch_protection.json")

    def collaborators(self) -> list[dict[str, Any]]:
        payload = self._read("collaborators.json")
        return payload if isinstance(payload, list) else payload.get("collaborators", [])

    def teams(self) -> list[dict[str, Any]]:
        payload = self._read("teams.json")
        return payload if isinstance(payload, list) else payload.get("teams", [])

    def workflow_permissions(self) -> dict[str, Any]:
        return self._read("workflow_permissions.json")

    def vulnerability_alerts(self) -> dict[str, Any]:
        return self._read("vulnerability_alerts.json")

    def _read(self, name: str) -> Any:
        path = self.fixture / name
        return read_json(path) if path.exists() else {"available": False}


def sync_repo_governance(
    repo: str,
    *,
    out: str | Path | None = None,
    fixture_dir: str | Path | None = None,
    token: str | None = None,
    token_env: str = "TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN",
    collected_at: datetime | None = None,
) -> list[dict[str, Any]]:
    spec = parse_repo_spec(repo)
    secret = token or os.environ.get(token_env)
    if fixture_dir:
        client: GitHubGovernanceClient | FixtureGovernanceClient = FixtureGovernanceClient(fixture_dir)
    elif secret:
        client = GitHubGovernanceClient(spec.owner, spec.repo, token=secret)
    else:
        raise ValueError("repo governance sync requires --fixture-dir or a GitHub App installation token")

    repo_data = client.repo()
    now = collected_at or datetime.now(UTC)
    rows = _build_events(
        spec,
        repo_data,
        client,
        now,
        credential_fingerprint=_fingerprint(secret) if secret else "fixture",
    )
    if out:
        write_jsonl(out, rows)
    return rows


def _build_events(
    spec: RepoSpec,
    repo: dict[str, Any],
    client: GitHubGovernanceClient | FixtureGovernanceClient,
    collected_at: datetime,
    *,
    credential_fingerprint: str,
) -> list[dict[str, Any]]:
    branch = str(repo.get("default_branch") or "main")
    source_health = {
        "credential_fingerprint": credential_fingerprint,
        "credential_boundary": "github_app_installation_token_or_fixture",
        "minimum_scopes": READ_ONLY_SCOPES,
        "collected_at": utc_iso(collected_at),
    }
    signal_payloads = {
        "branch_protection": _safe_call(lambda: client.branch_protection(branch)),
        "collaborators": _safe_call(client.collaborators),
        "teams": _safe_call(client.teams),
        "workflow_permissions": _safe_call(client.workflow_permissions),
        "security_settings": _safe_call(client.vulnerability_alerts),
    }
    return [
        _event(
            spec,
            collected_at,
            signal=signal,
            event_type=f"repository.governance.{signal}",
            controls=CONTROL_MAP[signal],
            evidence_ref=f"https://api.github.com/repos/{spec.slug}",
            attributes={
                "default_branch": branch,
                "source_health": source_health,
                "governance": _normalize_signal(signal, payload),
            },
            status=_status_for(payload),
        )
        for signal, payload in signal_payloads.items()
    ]


def _safe_call(func: Any) -> dict[str, Any] | list[dict[str, Any]]:
    try:
        return func()
    except urllib.error.HTTPError as exc:
        return {
            "available": False,
            "requires_scope_or_permission": True,
            "http_status": exc.code,
            "reason": "authenticated API did not authorize this signal",
        }


def _normalize_signal(signal: str, payload: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(payload, list):
        return {
            "signal": signal,
            "available": True,
            "count": len(payload),
            "items": [_redact_item(item) for item in payload],
        }
    if payload.get("available") is False:
        return {"signal": signal, **payload}
    return {"signal": signal, "available": True, **_redact_item(payload)}


def _redact_item(item: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in item.items():
        lowered = key.lower()
        if any(secret in lowered for secret in ("token", "secret", "password", "private_key")):
            redacted[key] = "[redacted]"
        elif isinstance(value, dict):
            redacted[key] = _redact_item(value)
        elif isinstance(value, list):
            redacted[key] = [_redact_item(v) if isinstance(v, dict) else v for v in value]
        else:
            redacted[key] = value
    return redacted


def _status_for(payload: dict[str, Any] | list[dict[str, Any]]) -> str:
    if isinstance(payload, dict) and payload.get("available") is False:
        return "requires_authenticated_connector"
    return "observed"


def _event(
    spec: RepoSpec,
    collected_at: datetime,
    *,
    signal: str,
    event_type: str,
    controls: list[str],
    evidence_ref: str,
    attributes: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    stable = _sha({"repo": spec.slug, "signal": signal})[:16]
    evidence_body = {"event_type": event_type, "evidence_ref": evidence_ref, "attributes": attributes}
    return {
        "event_id": f"repo-governance-{stable}",
        "tenant_id": "customer-managed",
        "workspace_id": "default",
        "event_time": utc_iso(collected_at),
        "source": "github-repo-governance",
        "event_type": event_type,
        "entity": {
            "asset_id": spec.asset_id,
            "asset_type": "repository",
            "asset_owner": spec.owner,
            "environment": "prod",
            "repo": spec.slug,
        },
        "severity": "info",
        "status": status,
        "controls": controls,
        "evidence": {
            "evidence_id": f"ev-{stable}",
            "evidence_ref": evidence_ref,
            "evidence_collected_at": utc_iso(collected_at),
            "raw_sha256": _sha(evidence_body),
        },
        "attributes": attributes,
    }


def _fingerprint(secret: str | None) -> str:
    if not secret:
        return "none"
    return f"sha256:{hashlib.sha256(secret.encode('utf-8')).hexdigest()[:12]}"


def _sha(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
