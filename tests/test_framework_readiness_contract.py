"""Framework readiness metadata must preserve honest planned boundaries."""

from security_lakehouse.framework_provenance import build_framework_view


def test_soc1_planned_view_explains_boundary_and_next_step() -> None:
    soc1 = next(row for row in build_framework_view() if row["framework_id"] == "soc1")

    assert soc1["implementation_status"] == "planned"
    assert soc1["coverage_boundary"]
    assert "service-specific" in soc1["coverage_boundary"]
    assert soc1["evidence_focus"]
    assert soc1["next_step"]


def test_planned_framework_readiness_metadata_does_not_create_controls() -> None:
    soc1 = next(row for row in build_framework_view() if row["framework_id"] == "soc1")

    assert soc1["control_count"] == 0
    assert soc1["implemented_control_count"] == 0
    assert soc1["mapping_coverage_pct"] == 0.0
