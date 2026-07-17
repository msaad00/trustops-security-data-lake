"""Regression contract for a compact audit-room proof workspace."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
PAGE = ROOT / "app/web/src/app/audit-room/page.tsx"


def test_audit_room_uses_compact_tabbed_workspace() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert "const AUDIT_ROOM_TABS" in page
    assert '"Freshness", "Runs", "Snapshots", "Gaps"' in page
    assert 'useState<AuditRoomTab>("Freshness")' in page
    assert 'aria-label="Audit room view"' in page
    assert "activeAuditTab ===" in page
    assert "Readiness summary" in page
    assert "EvidenceFreshnessSlaPanel" in page
    assert "IngestionLoopStrip" in page
    assert "AuditSnapshotTimeline" in page
    assert "Blocking gaps" in page


def test_audit_room_does_not_render_every_audit_surface_by_default() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert "<TrustPipelineStrip" not in page
    assert "<EvidenceFreshnessSlaPanel />" not in page
    assert "<IngestionLoopStrip />" not in page
    assert "<AuditRoomTrendsPanel />" not in page
    assert "<RemediationSlaStrip />" not in page
    assert "<AuditSnapshotTimeline />" not in page
    assert "Audit workflow checklist" not in page
    assert "Extended audit programs" not in page
