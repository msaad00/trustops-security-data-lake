"""Framework pack coverage tests."""

from __future__ import annotations

import json

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.framework_packs import (
    NIST_AI_RMF_SUBCATEGORY_COUNT,
    SOC2_COMMON_CRITERIA_COUNT,
    nist_ai_rmf_specs,
    soc2_common_criteria_specs,
    sync_framework_packs,
)
from security_lakehouse.mappings import load_control_article_mappings


def test_soc2_pack_has_all_common_criteria() -> None:
    specs = soc2_common_criteria_specs()
    assert len(specs) == SOC2_COMMON_CRITERIA_COUNT
    assert {spec.article_id for spec in specs} == {
        *(f"CC1.{i}" for i in range(1, 6)),
        *(f"CC2.{i}" for i in range(1, 4)),
        *(f"CC3.{i}" for i in range(1, 5)),
        *(f"CC4.{i}" for i in range(1, 3)),
        *(f"CC5.{i}" for i in range(1, 4)),
        *(f"CC6.{i}" for i in range(1, 9)),
        *(f"CC7.{i}" for i in range(1, 6)),
        "CC8.1",
        *(f"CC9.{i}" for i in range(1, 3)),
    }


def test_nist_ai_rmf_pack_has_all_subcategories() -> None:
    assert len(nist_ai_rmf_specs()) == NIST_AI_RMF_SUBCATEGORY_COUNT


def test_catalog_has_full_soc2_and_nist_packs() -> None:
    catalog = load_control_catalog()
    mappings = load_control_article_mappings()
    soc2 = [row for row in catalog.values() if row["framework_id"] == "soc2"]
    nist = [row for row in catalog.values() if row["framework_id"] == "nist-ai-rmf"]
    assert len(soc2) == SOC2_COMMON_CRITERIA_COUNT
    assert len(nist) == NIST_AI_RMF_SUBCATEGORY_COUNT
    assert all(row["control_id"] in mappings for row in soc2)
    assert all(row["control_id"] in mappings for row in nist)


def test_sync_packs_is_idempotent(tmp_path) -> None:
    catalog_copy = tmp_path / "catalog.json"
    mappings_copy = tmp_path / "control_articles.json"
    map_copy = tmp_path / "control_map.json"
    catalog_copy.write_text(
        json.dumps(
            {
                "catalog_version": "2026-06-30",
                "control_schema_version": "trustops.control.v2",
                "scope": "test",
                "controls": [],
            }
        ),
        encoding="utf-8",
    )
    mappings_copy.write_text(
        json.dumps({"schema": "trustops.mapping.v1", "mappings": []}),
        encoding="utf-8",
    )
    map_copy.write_text(json.dumps({"controls": []}), encoding="utf-8")
    first = sync_framework_packs(
        packs=["soc2"],
        catalog_path=catalog_copy,
        mappings_path=mappings_copy,
        control_map_path=map_copy,
        write_bundle=False,
    )
    second = sync_framework_packs(
        packs=["soc2"],
        catalog_path=catalog_copy,
        mappings_path=mappings_copy,
        control_map_path=map_copy,
        write_bundle=False,
    )
    assert first["added_controls"] == 33
    assert second["added_controls"] == 0
