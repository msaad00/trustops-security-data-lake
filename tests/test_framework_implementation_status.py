"""Framework implementation_status validation (#14)."""

from __future__ import annotations

from security_lakehouse.catalog import (
    FRAMEWORK_IMPLEMENTATION_STATUSES,
    validate_catalog,
)
from security_lakehouse.framework_coverage import build_framework_coverage, framework_coverage_summary


def test_validate_catalog_accepts_current_registry() -> None:
    assert validate_catalog() == []


def test_planned_frameworks_have_no_seeded_controls() -> None:
    rows = build_framework_coverage()
    planned = [row for row in rows if row.get("implementation_status") == "planned"]
    assert len(planned) >= 3
    assert all(int(row["seeded_control_count"]) == 0 for row in planned)


def test_coverage_summary_splits_implemented_and_planned() -> None:
    rows = build_framework_coverage()
    summary = framework_coverage_summary(rows)
    assert summary["framework_count"] == summary["implemented_framework_count"] + summary["planned_framework_count"]
    assert summary["planned_framework_count"] >= 3
    assert summary["implemented_framework_count"] == 10


def test_framework_status_enum_is_documented() -> None:
    assert "planned" in FRAMEWORK_IMPLEMENTATION_STATUSES
    assert "implemented_full_pack" in FRAMEWORK_IMPLEMENTATION_STATUSES
