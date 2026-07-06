from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from security_lakehouse import api_legacy, api_v1
from security_lakehouse.framework_detail import build_framework_detail
from security_lakehouse.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "security_events.jsonl"


def test_framework_detail_composes_controls_rules_evidence_and_sources(tmp_path: Path) -> None:
    run_pipeline(RAW, tmp_path / "lake")

    detail = build_framework_detail("soc2", tmp_path / "lake")

    assert detail is not None
    assert detail["framework"]["framework_id"] == "soc2"
    assert detail["summary"]["control_count"] >= 1
    assert detail["summary"]["mapped_control_count"] >= 1
    assert detail["summary"]["evidence_count"] >= 1
    control = next(row for row in detail["controls"] if row["control_id"] == "SOC2-CC6.1")
    assert control["evaluation_rule"]
    assert control["evidence_requirement"]
    assert control["articles"][0]["official_source_url"].startswith("https://")
    assert control["posture"]["status"] in {"pass", "fail"}
    assert control["test"]["required_evidence_types"]
    assert control["evidence"]["sources"]
    assert isinstance(control["connector_hints"], list)
    if control["connector_hints"]:
        assert control["connector_hints"][0]["connector_id"]
        assert "configured" in control["connector_hints"][0]


def test_framework_detail_routes_return_404_for_unknown_framework(tmp_path: Path) -> None:
    run_pipeline(RAW, tmp_path / "lake")

    status, body = api_legacy.handle_get("/api/frameworks/not-real/detail", {}, tmp_path / "lake")
    assert status == HTTPStatus.NOT_FOUND
    assert body == {"error": "not_found"}

    status, body = api_v1.handle_get("/api/v1/frameworks/not-real/detail", {}, tmp_path / "lake")
    assert status == HTTPStatus.NOT_FOUND
    assert body["errors"][0]["code"] == "not_found"


def test_framework_detail_routes_expose_same_composed_payload(tmp_path: Path) -> None:
    run_pipeline(RAW, tmp_path / "lake")

    legacy_status, legacy_body = api_legacy.handle_get("/api/frameworks/soc2/detail", {}, tmp_path / "lake")
    v1_status, v1_body = api_v1.handle_get("/api/v1/frameworks/soc2/detail", {}, tmp_path / "lake")

    assert legacy_status == HTTPStatus.OK
    assert v1_status == HTTPStatus.OK
    assert legacy_body == v1_body["data"]
    assert v1_body["meta"]["resource"] == "framework.detail"
