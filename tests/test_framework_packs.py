"""Framework pack coverage tests."""

from __future__ import annotations

import json

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.framework_packs import (
    NIST_AI_RMF_SUBCATEGORY_COUNT,
    NIST_CSF_2_SUBCATEGORY_COUNT,
    SOC2_COMMON_CRITERIA_COUNT,
    SOC2_FULL_PACK_COUNT,
    SOC2_TSC_EXTENSION_COUNT,
    cis_aws_v3_specs,
    fedramp_moderate_specs,
    iso_27001_2022_specs,
    iso_27017_2015_specs,
    iso_42001_2023_specs,
    nist_ai_rmf_specs,
    nist_csf_2_specs,
    soc2_common_criteria_specs,
    soc2_full_pack_specs,
    soc2_tsc_extension_specs,
    sync_framework_packs,
)
from security_lakehouse.mappings import load_control_article_mappings
from security_lakehouse.pack_data import (
    CIS_AWS_V3_COUNT,
    FEDRAMP_MODERATE_COUNT,
    ISO_27001_2022_ANNEX_A_COUNT,
    ISO_27017_2015_COUNT,
    ISO_42001_2023_ANNEX_A_COUNT,
    NIST_CSF_2_COUNT,
    cis_aws_v3_requirements,
    iso_27017_2015_controls,
)


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


def test_soc2_pack_has_tsc_extensions() -> None:
    specs = soc2_tsc_extension_specs()
    assert len(specs) == SOC2_TSC_EXTENSION_COUNT
    assert {spec.article_id for spec in specs} == {
        *(f"A1.{i}" for i in range(1, 4)),
        *(f"C1.{i}" for i in range(1, 3)),
        *(f"PI1.{i}" for i in range(1, 6)),
        "P1.1",
        "P2.1",
        *(f"P3.{i}" for i in range(1, 3)),
        *(f"P4.{i}" for i in range(1, 4)),
        *(f"P5.{i}" for i in range(1, 3)),
        *(f"P6.{i}" for i in range(1, 8)),
        "P7.1",
        "P8.1",
    }


def test_soc2_full_pack_has_all_sixty_one_criteria() -> None:
    assert len(soc2_full_pack_specs()) == SOC2_FULL_PACK_COUNT


def test_nist_ai_rmf_pack_has_all_subcategories() -> None:
    assert len(nist_ai_rmf_specs()) == NIST_AI_RMF_SUBCATEGORY_COUNT


def test_nist_csf_2_pack_has_all_subcategories() -> None:
    specs = nist_csf_2_specs()
    assert len(specs) == NIST_CSF_2_SUBCATEGORY_COUNT
    assert len(specs) == NIST_CSF_2_COUNT
    assert specs[0].framework_id == "nist-csf-2.0"
    assert specs[0].control_id.startswith("NIST-CSF-")


def test_fedramp_pack_has_nist_moderate_baseline() -> None:
    specs = fedramp_moderate_specs()
    assert len(specs) == FEDRAMP_MODERATE_COUNT
    assert specs[0].framework_id == "fedramp-moderate"
    assert specs[0].control_id.startswith("FEDRAMP-")


def test_cis_aws_pack_has_all_v3_recommendations() -> None:
    specs = cis_aws_v3_specs()
    assert len(specs) == CIS_AWS_V3_COUNT
    article_ids = {spec.article_id for spec in specs}
    assert len(article_ids) == CIS_AWS_V3_COUNT
    expected = {req_id for req_id, _title in cis_aws_v3_requirements()}
    assert article_ids == expected


def test_iso_packs_have_full_annex_a_counts() -> None:
    assert len(iso_27001_2022_specs()) == ISO_27001_2022_ANNEX_A_COUNT
    assert len(iso_42001_2023_specs()) == ISO_42001_2023_ANNEX_A_COUNT


def test_iso_27017_pack_has_all_cloud_clause_ids() -> None:
    specs = iso_27017_2015_specs()
    assert len(specs) == ISO_27017_2015_COUNT
    article_ids = {spec.article_id for spec in specs}
    expected = {article_id for article_id, _title in iso_27017_2015_controls()}
    assert article_ids == expected
    cld_ids = {spec.article_id for spec in specs if spec.article_id.startswith("CLD.")}
    assert len(cld_ids) == 7
    assert specs[0].framework_id == "iso-27017-2015"
    assert specs[0].control_id.startswith("ISO27017-")


def test_catalog_has_full_core_framework_packs() -> None:
    catalog = load_control_catalog()
    mappings = load_control_article_mappings()
    expectations = {
        "soc2": SOC2_FULL_PACK_COUNT,
        "nist-ai-rmf": NIST_AI_RMF_SUBCATEGORY_COUNT,
        "nist-csf-2.0": NIST_CSF_2_COUNT,
        "fedramp-moderate": FEDRAMP_MODERATE_COUNT,
        "cis_aws": CIS_AWS_V3_COUNT,
        "iso-27001-2022": ISO_27001_2022_ANNEX_A_COUNT,
        "iso-27017-2015": ISO_27017_2015_COUNT,
        "iso-42001-2023": ISO_42001_2023_ANNEX_A_COUNT,
    }
    for framework_id, minimum in expectations.items():
        rows = [row for row in catalog.values() if row["framework_id"] == framework_id]
        assert len(rows) >= minimum, framework_id
        assert all(row["control_id"] in mappings for row in rows)


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
    assert first["added_controls"] == SOC2_FULL_PACK_COUNT
    assert second["added_controls"] == 0
