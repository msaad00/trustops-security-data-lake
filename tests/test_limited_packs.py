"""Tests for limited-mapping framework packs (GDPR, HIPAA, PCI, EU AI Act)."""

from __future__ import annotations

from security_lakehouse.catalog import load_control_catalog, validate_catalog
from security_lakehouse.limited_packs import LIMITED_PACK_BUILDERS, LIMITED_PACK_MINIMUMS
from security_lakehouse.mappings import load_control_article_mappings


def test_limited_pack_builders_emit_expected_counts() -> None:
    for pack_id, builder in LIMITED_PACK_BUILDERS.items():
        specs = list(builder())
        assert len(specs) >= 9, f"{pack_id} should emit a meaningful subset"


def test_limited_frameworks_meet_minimum_seeded_counts() -> None:
    catalog = load_control_catalog()
    mappings = load_control_article_mappings()
    for framework_id, minimum in LIMITED_PACK_MINIMUMS.items():
        controls = [c for c in catalog.values() if c["framework_id"] == framework_id]
        assert len(controls) >= minimum, f"{framework_id} expected >={minimum}, got {len(controls)}"
        mapped = [c for c in controls if c["control_id"] in mappings]
        assert len(mapped) == len(controls), f"{framework_id} controls must all have mappings"


def test_catalog_validates_after_limited_pack_sync() -> None:
    errors = validate_catalog()
    assert errors == [], errors
