from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from security_lakehouse.assessment import build_current_posture, write_assessment_snapshot
from security_lakehouse.catalog import (
    load_control_catalog,
    load_framework_registry,
    validate_catalog,
    validate_evidence_controls,
)
from security_lakehouse.connectors import load_connector_catalog, validate_connector_catalog
from security_lakehouse.dashboard import render_dashboard
from security_lakehouse.io import read_json, read_jsonl
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.programs import validate_program_catalog
from security_lakehouse.validation import validate_raw_events

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "security_events.jsonl"


def test_sample_raw_events_are_valid() -> None:
    rows = read_jsonl(RAW)

    assert validate_raw_events(rows) == []
    assert len(rows) == 10


def test_framework_registry_and_catalog_are_official_source_linked() -> None:
    registry = load_framework_registry()
    catalog = load_control_catalog()

    assert validate_catalog() == []
    # Every framework in the registry must declare an official source URL
    # and have at least one control mapped to it. Specific framework IDs
    # change as the catalog grows — this assertion guards the contract,
    # not the snapshot.
    expected = {
        "soc2",
        "nist-ai-rmf",
        "iso-27001-2022",
        "hipaa-security-rule",
        "pci-dss-v4",
        "gdpr-2016-679",
        "eu-ai-act-2024-1689",
        "iso-42001-2023",
    }
    assert expected.issubset(set(registry))
    assert set(registry) == {control["framework_id"] for control in catalog.values()} | (
        set(registry) - {control["framework_id"] for control in catalog.values()}
    )
    for framework_id, framework in registry.items():
        assert framework["official_source_url"].startswith("https://"), framework_id
    # Keep the spot-checks on the seed frameworks so the test still catches
    # accidental URL drift on the controls we ship out of the box.
    assert registry["soc2"]["official_source_url"].startswith("https://www.aicpa-cima.com/")
    assert registry["nist-ai-rmf"]["official_source_url"].startswith("https://www.nist.gov/")


def test_sample_evidence_references_only_implemented_controls() -> None:
    rows = read_jsonl(RAW)
    referenced = {control for row in rows for control in row.get("controls", [])}

    assert validate_evidence_controls(referenced) == []


def test_program_catalog_maps_to_implemented_controls() -> None:
    assert validate_program_catalog() == []


def test_connector_catalog_uses_least_privilege_access_boundaries() -> None:
    connectors = load_connector_catalog()

    assert validate_connector_catalog() == []
    assert {"snowflake-evidence-lake", "clickhouse-telemetry-lake", "managed-local-evidence"} <= set(connectors)
    assert connectors["snowflake-evidence-lake"]["access_boundary"] == "read_only_role"
    assert connectors["clickhouse-telemetry-lake"]["default_route"] == "ClickHouse"
    assert connectors["managed-local-evidence"]["collection_mode"] == "managed_evidence_object"


def test_pipeline_writes_bronze_silver_gold_and_mart(tmp_path: Path) -> None:
    result = run_pipeline(RAW, tmp_path / "lake")

    assert result.raw_count == 10
    assert result.silver_count == 10
    assert result.control_count == 4
    assert Path(result.mart_path).exists()

    bronze = read_jsonl(tmp_path / "lake" / "bronze" / "raw_events.jsonl")
    silver = read_jsonl(tmp_path / "lake" / "silver" / "normalized_events.jsonl")
    metrics = read_json(result.metrics_path)
    dashboard_data = read_json(result.dashboard_data_path)
    current_posture = read_json(tmp_path / "lake" / "gold" / "current_posture.json")
    control_tests = read_jsonl(tmp_path / "lake" / "gold" / "control_tests.jsonl")
    manifest = read_json(tmp_path / "lake" / "manifest.json")

    assert len(bronze[0]["raw_sha256"]) == 64
    assert silver[0]["asset_id"] == "aws:iam:role/ml-prod-agent"
    assert metrics["critical_open"] == 2
    assert metrics["runtime_block_rate"] == 1.0
    assert metrics["top_risk_asset"] == "container:rag-api@sha256:91ab"
    assert metrics["control_test_count"] == 4
    assert metrics["failing_control_tests"] >= 1
    assert [backend["name"] for backend in dashboard_data["lake_backends"]] == ["Snowflake", "ClickHouse"]
    assert len(dashboard_data["control_tests"]) == 4
    assert {row["program_id"] for row in control_tests} == {"acme-continuous-trust"}
    assert all(row["confidence_score"] > 0 for row in control_tests)
    assert any(row["result"] == "fail" and row["status"] == "failing" for row in control_tests)
    assert current_posture["assessment_type"] == "current_posture"
    assert current_posture["posture"]["state"] == "critical"
    assert current_posture["posture"]["open_violation_count"] > 0
    assert manifest["marts"]["sqlite"].endswith("security_lakehouse.sqlite")
    assert manifest["zones"]["gold_control_tests"].endswith("control_tests.jsonl")
    assert manifest["storage_roles"]["duckdb"] == "optional local analytical mart for columnar datasets"
    if result.duckdb_mart_path is not None:
        assert Path(result.duckdb_mart_path).exists()
    else:
        assert manifest["marts"]["duckdb"] is None

    with sqlite3.connect(result.mart_path) as conn:
        failing = conn.execute("select count(*) from control_posture where status = 'fail'").fetchone()[0]
        failing_tests = conn.execute("select count(*) from control_tests where result = 'fail'").fetchone()[0]
        top_asset = conn.execute("select asset_id from asset_risk order by risk_score desc limit 1").fetchone()[0]

    assert failing >= 1
    assert failing_tests >= 1
    assert top_asset == "container:rag-api@sha256:91ab"


def test_dashboard_render_tolerates_empty_lake(tmp_path: Path) -> None:
    # First-boot scenario: the container mounts an empty lake. Render must
    # still produce a self-contained HTML (no crash on missing gold files).
    empty_lake = tmp_path / "empty"
    empty_lake.mkdir()
    out = render_dashboard(empty_lake, tmp_path / "empty.html")
    html = out.read_text(encoding="utf-8")
    assert "Trust Home" in html
    assert "TrustOps" in html


def test_dashboard_render_uses_gold_data(tmp_path: Path) -> None:
    run_pipeline(RAW, tmp_path / "lake")

    output = render_dashboard(tmp_path / "lake", tmp_path / "dashboard" / "index.html")

    html = output.read_text(encoding="utf-8")
    # Either the React single-file export (when web/dist/ is packaged) or the
    # offline fallback packet must surface the Trust Home heading and embed the
    # current assessment payload for the auditor downstream of the export.
    assert "Trust Home" in html
    assert "TrustOps" in html
    assert "SOC2-CC6.1" in html
    assert "container:rag-api@sha256:91ab" in html
    # Data payload is injected for hydration / offline review.
    assert '<script id="app-data"' in html
    # Output must be self-contained — no fetched <script src> or <link href>
    # may point at /console/_next/... after inlining. (Webpack runtime still
    # carries the chunk URLs as string literals inside the inlined JS for its
    # internal lookup table; that's expected and never triggers a network
    # request because every chunk is already in the bundle.)
    assert 'src="/console/_next/' not in html
    assert 'href="/console/_next/' not in html


def test_assessment_engine_builds_current_and_point_in_time_posture(tmp_path: Path) -> None:
    run_pipeline(RAW, tmp_path / "lake")

    posture = build_current_posture(
        tmp_path / "lake",
        now=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
    )
    snapshot = write_assessment_snapshot(
        tmp_path / "lake",
        output=tmp_path / "snapshot.json",
        reason="vendor_due_diligence",
    )

    assert posture["assessment_type"] == "current_posture"
    assert posture["posture"]["state"] == "critical"
    assert posture["posture"]["critical_violation_count"] >= 1
    assert posture["posture"]["failed_control_test_count"] >= 1
    assert posture["frameworks"][0]["score"] <= 100
    assert any(item["control_id"] == "SOC2-CC6.1" for item in posture["violations"])
    assert len(posture["assessment_hash"]) == 64

    snapshot_payload = read_json(snapshot)
    assert snapshot_payload["assessment_type"] == "point_in_time_snapshot"
    assert snapshot_payload["snapshot_reason"] == "vendor_due_diligence"


def test_validation_rejects_duplicate_event_ids() -> None:
    rows = [
        {
            "event_id": "evt-1",
            "tenant_id": "tenant",
            "event_time": "2026-05-20T00:00:00Z",
            "source": "scanner",
            "event_type": "finding",
            "entity": {"asset_id": "asset-1"},
        },
        {
            "event_id": "evt-1",
            "tenant_id": "tenant",
            "event_time": "2026-05-20T00:00:00Z",
            "source": "scanner",
            "event_type": "finding",
            "entity": {"asset_id": "asset-1"},
        },
    ]

    errors = validate_raw_events(rows)

    assert any("duplicate event_id" in error for error in errors)
