"""NIST AI RMF subcategory titles come from the pinned NIST AI 100-1 text."""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.catalog_versions import controls_as_of
from security_lakehouse.mappings import load_control_article_mappings

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "frameworks/packs/data/nist_ai_rmf.json").read_text())


def test_manifest_carries_an_official_statement_for_every_subcategory() -> None:
    rows = MANIFEST["rows"]
    assert len(rows) == 72
    assert len(MANIFEST["source"]["pdf_sha256"]) == 64
    for row in rows:
        assert row["statement"].endswith(".")
        assert row["statement"].startswith(row["title"])
        assert "Continued" not in row["statement"] and "Page " not in row["statement"]


def test_catalog_titles_are_the_official_statements() -> None:
    by_ref = {row["id"]: row for row in MANIFEST["rows"]}
    controls = {cid: c for cid, c in load_control_catalog().items() if c["framework_id"] == "nist-ai-rmf"}
    mappings = load_control_article_mappings()
    assert len(controls) == 72
    for control_id, control in controls.items():
        ref = control_id.removeprefix("NIST-AI-RMF-")
        assert control["title"] == f"{ref.replace('-', ' ')} — {by_ref[ref]['title']}"
        assert control["supersedes"] == f"{control_id}@1.0.0"
        assert mappings[control_id]["articles"][0]["title"] == by_ref[ref]["title"][:240]


def test_prior_boilerplate_titles_remain_in_history() -> None:
    before = {cid: c for cid, c in controls_as_of("2026-09-01").items() if c["framework_id"] == "nist-ai-rmf"}
    assert len(before) == 72
    assert all(c["version"] == "1.0.0" for c in before.values())
