"""Regression contract for a compact, source-aligned dashboard overview."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "app/web/src/app/dashboard/page.tsx"


def test_dashboard_overview_is_source_aligned_and_tabbed() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")

    assert "const DASHBOARD_TABS" in dashboard
    assert '"Sources", "Controls", "Proof"' in dashboard
    assert 'aria-label="Dashboard view"' in dashboard
    assert "Evidence loop" in dashboard
    assert "Connected sources" in dashboard
    assert "Raw evidence" in dashboard
    assert "Control eval" in dashboard
    assert "Proof export" in dashboard
    assert "Security data lake" in dashboard
    assert "activeDashboardTab ===" in dashboard
