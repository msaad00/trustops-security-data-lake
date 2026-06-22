"""Optional agent harness tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from security_lakehouse.agents import build_posture_review_graph, run_posture_review
from security_lakehouse.agents.model_client import ModelClientError
from security_lakehouse.agents.model_contract import validate_model_output
from security_lakehouse.agents.providers import ModelProviderConfig, provider_from_env
from security_lakehouse.cli import main
from test_api_v1 import _seed_lake


def _seed_gap(lake: Path) -> None:
    _seed_lake(lake)
    rows = [
        {
            "test_id": "test-soc2",
            "control_id": "SOC2-CC6.1",
            "framework": "SOC 2",
            "owner": "security-platform",
            "status": "needs_evidence",
            "missing_evidence_types": ["identity.access_review"],
            "stale_evidence_types": [],
            "expired_evidence_types": ["mfa.status"],
            "freshness_status": "expired",
        }
    ]
    (lake / "gold" / "control_tests.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_posture_review_runs_without_langgraph_or_llm(tmp_path: Path) -> None:
    _seed_gap(tmp_path)

    state = run_posture_review(tmp_path, role="read_only")

    assert state["mode"] == "rules_only"
    assert state["posture"]["posture"]["control_count"] >= 1
    assert state["evidence_gaps"][0]["control_id"] == "SOC2-CC6.1"
    assert state["decisions"][0].action == "create_evidence_request"
    assert state["decisions"][0].requires_approval is True
    assert state["decisions"][0].status == "proposed"


def test_posture_review_uses_role_redaction(tmp_path: Path) -> None:
    _seed_gap(tmp_path)

    state = run_posture_review(tmp_path, role="auditor")

    assert state["evidence_gaps"][0]["owner"] == "[redacted]"


def test_langgraph_builder_is_optional() -> None:
    if importlib.util.find_spec("langgraph") is not None:
        assert build_posture_review_graph() is not None
        return

    with pytest.raises(RuntimeError, match="install trustops-security-data-lake\\[agents\\]"):
        build_posture_review_graph()


def test_provider_configured_without_use_model_stays_deterministic(tmp_path: Path) -> None:
    _seed_gap(tmp_path)
    provider = ModelProviderConfig(provider="ollama", model="llama3.1", base_url="http://127.0.0.1:11434")

    state = run_posture_review(tmp_path, role="read_only", provider=provider)

    assert state["mode"] == "rules_only"
    assert state["model_provider"]["configured"] is True
    assert state["model_provider"]["use_model"] is False
    assert state["model_context"]["policy"]["compliance_truth"].startswith("TrustOps deterministic")
    assert "model_output" not in state
    assert state["errors"] == []


def test_model_assisted_run_validates_model_output(tmp_path: Path) -> None:
    _seed_gap(tmp_path)
    provider = ModelProviderConfig(
        provider="ollama",
        model="llama3.1",
        base_url="http://127.0.0.1:11434",
        use_model=True,
    )

    def fake_model(context: dict, configured: ModelProviderConfig) -> dict:
        assert configured.provider == "ollama"
        assert context["facts"]["evidence_gaps"][0]["control_id"] == "SOC2-CC6.1"
        return {
            "summary": "Evidence is missing for access review.",
            "priorities": [{"control_id": "SOC2-CC6.1", "reason": "expired MFA status", "rank": 1}],
            "proposed_tool_calls": [
                {
                    "name": "create_remediation_task",
                    "arguments": {"control_id": "SOC2-CC6.1", "reason": "owner follow-up"},
                },
                {"name": "mark_control_passed", "arguments": {"control_id": "SOC2-CC6.1"}},
            ],
        }

    state = run_posture_review(tmp_path, role="read_only", provider=provider, model_client=fake_model)

    assert state["mode"] == "model_assisted"
    assert state["model_output"]["summary"] == "Evidence is missing for access review."
    assert state["model_output"]["priorities"][0]["control_id"] == "SOC2-CC6.1"
    assert state["model_output"]["proposed_tool_calls"][0]["requires_approval"] is True
    assert state["model_output"]["rejected_tool_calls"] == ["mark_control_passed"]
    assert state["decisions"][0].requires_approval is True
    assert state["decisions"][0].status == "proposed"


def test_model_client_error_is_non_fatal(tmp_path: Path) -> None:
    _seed_gap(tmp_path)
    provider = ModelProviderConfig(
        provider="ollama",
        model="llama3.1",
        base_url="http://127.0.0.1:11434",
        use_model=True,
    )

    def failing_model(_context: dict, _configured: ModelProviderConfig) -> dict:
        raise ModelClientError("offline")

    state = run_posture_review(tmp_path, role="read_only", provider=provider, model_client=failing_model)

    assert state["mode"] == "rules_only"
    assert state["errors"] == ["model_error: offline"]
    assert state["decisions"][0].action == "create_evidence_request"


def test_validate_model_output_rejects_unsupported_tools() -> None:
    output = validate_model_output(
        {
            "summary": "x",
            "priorities": [{"control_id": "SOC2-CC7.2"}],
            "proposed_tool_calls": [
                {"name": "freeze_snapshot", "arguments": {"reason": "audit"}},
                {"name": "delete_evidence", "arguments": {}},
            ],
        }
    )

    assert output["proposed_tool_calls"] == [
        {"name": "freeze_snapshot", "arguments": {"reason": "audit"}, "requires_approval": True, "status": "proposed"}
    ]
    assert output["rejected_tool_calls"] == ["delete_evidence"]


def test_provider_env_requires_explicit_model_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTOPS_AGENT_PROVIDER", "ollama")
    monkeypatch.setenv("TRUSTOPS_AGENT_MODEL", "llama3.1")
    monkeypatch.delenv("TRUSTOPS_AGENT_USE_MODEL", raising=False)

    provider = provider_from_env()

    assert provider.provider == "ollama"
    assert provider.enabled is True
    assert provider.should_call_model is False


def test_posture_review_cli_outputs_json(tmp_path: Path, capsys) -> None:
    _seed_gap(tmp_path)

    assert main(["agents", "posture-review", "--lake", str(tmp_path), "--role", "auditor"]) == 0
    out = json.loads(capsys.readouterr().out)

    assert out["mode"] == "rules_only"
    assert out["role"] == "auditor"
    assert out["evidence_gaps"][0]["owner"] == "[redacted]"
    assert out["decisions"][0]["requires_approval"] is True


def test_posture_review_cli_can_build_model_context_without_call(tmp_path: Path, capsys) -> None:
    _seed_gap(tmp_path)

    assert (
        main(
            [
                "agents",
                "posture-review",
                "--lake",
                str(tmp_path),
                "--provider",
                "ollama",
                "--model",
                "llama3.1",
                "--base-url",
                "http://127.0.0.1:11434",
            ]
        )
        == 0
    )
    out = json.loads(capsys.readouterr().out)

    assert out["mode"] == "rules_only"
    assert out["model_provider"]["configured"] is True
    assert out["model_context"]["tool_manifest"][0]["name"] == "load_redacted_posture"
