"""Generic manifest-driven framework pack builder tests.

``pack_from_manifest`` reads a JSON manifest (identifiers, titles, source
citation) and applies a small named transform function (risk-domain lookups,
ID normalization, evidence-requirement wording) to produce
:class:`PackControlSpec` rows — replacing a full bespoke ``*_specs()``
function per framework with data + a thin transform.
"""

from __future__ import annotations

import json

import pytest

from security_lakehouse.pack_manifest import load_pack_manifest, pack_from_manifest
from security_lakehouse.pack_spec import PackControlSpec


def _write_manifest(tmp_path, payload):
    path = tmp_path / "sample_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_pack_manifest_reads_object_rows_and_source(tmp_path):
    path = _write_manifest(
        tmp_path,
        {
            "schema": "trustops.framework_pack_manifest.v1",
            "source": {"url": "https://example.org/spec", "name": "Example Spec"},
            "rows": [
                {"id": "1.1", "title": "First control"},
                {"id": "1.2", "title": "Second control"},
            ],
        },
    )
    manifest = load_pack_manifest(path)
    assert manifest.schema == "trustops.framework_pack_manifest.v1"
    assert manifest.source["url"] == "https://example.org/spec"
    assert [row.id for row in manifest.rows] == ["1.1", "1.2"]
    assert [row.title for row in manifest.rows] == ["First control", "Second control"]


def test_load_pack_manifest_reads_dict_rows_like_csf_core(tmp_path):
    path = _write_manifest(
        tmp_path,
        {
            "source": {"url": "https://example.org/outcomes"},
            "outcomes": {"GV.OC-01": "Mission is understood", "GV.OC-02": "Stakeholders are understood"},
        },
    )
    manifest = load_pack_manifest(path, rows_key="outcomes")
    assert [row.id for row in manifest.rows] == ["GV.OC-01", "GV.OC-02"]
    assert manifest.rows[0].title == "Mission is understood"


def test_load_pack_manifest_reads_plain_string_rows(tmp_path):
    path = _write_manifest(
        tmp_path,
        {"source": {"url": "https://example.org"}, "control_ids": ["AC-1", "AC-2"]},
    )
    manifest = load_pack_manifest(path, rows_key="control_ids")
    assert [row.id for row in manifest.rows] == ["AC-1", "AC-2"]
    assert all(row.title == "" for row in manifest.rows)


def test_load_pack_manifest_passes_through_extra_row_fields(tmp_path):
    path = _write_manifest(
        tmp_path,
        {
            "source": {"url": "https://example.org"},
            "rows": [{"id": "Art.5", "title": "Processing principles", "risk_domain": "privacy-engineering"}],
        },
    )
    manifest = load_pack_manifest(path)
    assert manifest.rows[0].extra == {"risk_domain": "privacy-engineering"}


def test_pack_from_manifest_produces_rows_matching_declared_fields(tmp_path):
    path = _write_manifest(
        tmp_path,
        {
            "source": {"url": "https://example.org/spec"},
            "rows": [
                {"id": "1.1", "title": "First control"},
                {"id": "1.2", "title": "Second control"},
            ],
        },
    )

    def transform(row):
        return PackControlSpec(
            control_id=f"SAMPLE-{row.id}",
            framework_id="sample",
            framework="Sample Framework",
            framework_ref=f"Sample {row.id}",
            article_id=row.id,
            title=row.title,
            risk_domain="governance",
            owner="grc",
            evaluation_rule="fail_when_missing_evidence",
            evidence_requirement=f"Evidence for {row.id}",
            asset_types=("service",),
            source_url="https://example.org/spec",
            official_source_ref="sample",
        )

    specs = pack_from_manifest(path, transform=transform)
    assert len(specs) == 2
    assert specs[0] == PackControlSpec(
        control_id="SAMPLE-1.1",
        framework_id="sample",
        framework="Sample Framework",
        framework_ref="Sample 1.1",
        article_id="1.1",
        title="First control",
        risk_domain="governance",
        owner="grc",
        evaluation_rule="fail_when_missing_evidence",
        evidence_requirement="Evidence for 1.1",
        asset_types=("service",),
        source_url="https://example.org/spec",
        official_source_ref="sample",
    )
    assert [spec.article_id for spec in specs] == ["1.1", "1.2"]


def test_load_pack_manifest_normalizes_string_source_citation(tmp_path):
    """Some pre-existing pack data files (e.g. cis_aws_v3.json) carry a plain
    string "source" citation plus a sibling "official_source_url", instead of
    the nist_csf_2_core.json precedent's {"url": ...} object. The loader must
    read those unmodified, since other modules read them directly too."""
    path = _write_manifest(
        tmp_path,
        {
            "source": "CIS Amazon Web Services Foundations Benchmark v3.0.0",
            "official_source_url": "https://www.cisecurity.org/benchmark/amazon_web_services",
            "requirements": [{"id": "1.1", "title": "Example"}],
        },
    )
    manifest = load_pack_manifest(path, rows_key="requirements")
    assert manifest.source["name"] == "CIS Amazon Web Services Foundations Benchmark v3.0.0"
    assert manifest.source["url"] == "https://www.cisecurity.org/benchmark/amazon_web_services"


def test_pack_from_manifest_missing_rows_key_raises(tmp_path):
    path = _write_manifest(tmp_path, {"source": {"url": "https://example.org"}})
    with pytest.raises(KeyError):
        pack_from_manifest(path, transform=lambda row: row)
