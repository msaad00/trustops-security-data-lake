"""Regression contract for a compact, source-aligned dashboard overview."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "app/web/src/app/dashboard/page.tsx"


def test_dashboard_overview_is_source_aligned_and_tabbed() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")

    assert "const DASHBOARD_TABS" in dashboard
    assert '"Posture", "Sources", "Proof"' in dashboard
    assert 'useState<DashboardTab>("Posture")' in dashboard
    assert 'aria-label="Dashboard view"' in dashboard
    assert "Current assessment" in dashboard
    assert "Framework posture" in dashboard
    assert "Control pass rate" in dashboard
    assert "Open findings" in dashboard
    assert "Proof export" in dashboard
    assert "Security data lake" in dashboard
    assert "activeDashboardTab ===" in dashboard
    assert "Evidence loop" not in dashboard
