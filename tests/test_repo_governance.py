"""Authenticated repository governance connector tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from security_lakehouse.cli import main
from security_lakehouse.io import read_jsonl
from security_lakehouse.repo_governance import sync_repo_governance
from security_lakehouse.validation import validate_raw_events


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    fixture = tmp_path / "governance-fixture"
    _write_json(
        fixture / "repo.json",
        {
            "default_branch": "main",
            "full_name": "acme/private-agent-api",
            "name": "private-agent-api",
            "private": True,
            "visibility": "private",
        },
    )
    _write_json(
        fixture / "branch_protection.json",
        {
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": True,
                "required_approving_review_count": 2,
                "require_code_owner_reviews": True,
            },
            "required_status_checks": {"strict": True, "contexts": ["quality", "web", "smoke"]},
            "enforce_admins": {"enabled": True},
        },
    )
    _write_json(
        fixture / "collaborators.json",
        [
            {"login": "alice", "role_name": "admin", "permissions": {"admin": True}, "token": "do-not-emit"},
            {"login": "bob", "role_name": "maintain", "permissions": {"maintain": True}},
        ],
    )
    _write_json(fixture / "teams.json", [{"name": "security", "permission": "admin", "privacy": "closed"}])
    _write_json(
        fixture / "workflow_permissions.json",
        {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False},
    )
    _write_json(fixture / "vulnerability_alerts.json", {"enabled": True})
    return fixture


def test_governance_sync_fixture_emits_valid_raw_events(tmp_path: Path) -> None:
    rows = sync_repo_governance(
        "acme/private-agent-api",
        fixture_dir=_fixture(tmp_path),
        collected_at=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )
    assert validate_raw_events(rows) == []
    by_type = {row["event_type"]: row for row in rows}
    assert set(by_type) == {
        "repository.governance.branch_protection",
        "repository.governance.collaborators",
        "repository.governance.security_settings",
        "repository.governance.teams",
        "repository.governance.workflow_permissions",
    }
    branch = by_type["repository.governance.branch_protection"]
    assert branch["controls"] == ["SOC2-CC6.1", "ISO27001-A.5.15", "PCI-DSS-7"]
    assert branch["attributes"]["governance"]["required_pull_request_reviews"]["required_approving_review_count"] == 2


def test_governance_sync_redacts_secret_like_fields(tmp_path: Path) -> None:
    rows = sync_repo_governance(
        "acme/private-agent-api",
        fixture_dir=_fixture(tmp_path),
        token="github_app_installation_token_value",
        collected_at=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )
    body = json.dumps(rows, sort_keys=True)
    assert "github_app_installation_token_value" not in body
    assert "do-not-emit" not in body
    assert "sha256:" in body
    collaborators = next(row for row in rows if row["event_type"] == "repository.governance.collaborators")
    assert collaborators["attributes"]["governance"]["items"][0]["token"] == "[redacted]"


def test_governance_sync_requires_fixture_or_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN", raising=False)
    with pytest.raises(ValueError, match="requires --fixture-dir"):
        sync_repo_governance("acme/private-agent-api")


def test_gitlab_governance_sync_fixture_emits_valid_raw_events(tmp_path: Path) -> None:
    rows = sync_repo_governance(
        "https://gitlab.com/acme/private-agent-api",
        fixture_dir=_fixture(tmp_path),
        provider="gitlab",
        collected_at=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )
    assert validate_raw_events(rows) == []
    assert rows[0]["source"] == "gitlab-repo-governance"
    assert rows[0]["entity"]["asset_id"] == "gitlab:repo:acme/private-agent-api"
    assert len(rows) == 5


def test_gitlab_governance_sync_redacts_secret_like_fields(tmp_path: Path) -> None:
    rows = sync_repo_governance(
        "acme/private-agent-api",
        fixture_dir=_fixture(tmp_path),
        provider="gitlab",
        token="gitlab_access_token_value",
        collected_at=datetime(2026, 5, 24, 12, 0, tzinfo=UTC),
    )
    body = json.dumps(rows, sort_keys=True)
    assert "gitlab_access_token_value" not in body
    assert rows[0]["attributes"]["source_health"]["provider"] == "gitlab"


def test_governance_sync_cli_writes_jsonl(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "repo-governance.jsonl"
    code = main(
        [
            "repo",
            "governance-sync",
            "acme/private-agent-api",
            "--fixture-dir",
            str(_fixture(tmp_path)),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 5
    rows = read_jsonl(out)
    assert validate_raw_events(rows) == []
