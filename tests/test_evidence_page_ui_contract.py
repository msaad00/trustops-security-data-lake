"""UI contract for separating evidence facts from report exports."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
EVIDENCE_PAGE = ROOT / "app/web/src/app/evidence/page.tsx"


def test_evidence_page_names_facts_reports_and_export_destinations() -> None:
    page = EVIDENCE_PAGE.read_text(encoding="utf-8")

    assert "These rows are evidence facts, not reports." in page
    assert "Security data lake layers" in page
    assert "Bronze raw" in page
    assert "Silver facts" in page
    assert "Gold posture" in page
    assert "Reports and proof packs" in page
    assert 'href: "/audit-room"' in page
    assert 'href: "/connectors"' in page
