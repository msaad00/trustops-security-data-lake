"""Regression contract for a compact, source-aligned dashboard overview."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
DASHBOARD = ROOT / "app/web/src/app/dashboard/page.tsx"
READINESS = ROOT / "app/web/src/components/dashboard/ReadinessGrid.tsx"
SIGNAL_FLOW = ROOT / "app/web/src/components/dashboard/TrustSignalFlow.tsx"
NEXT_CONFIG = ROOT / "app/web/next.config.ts"


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


def test_dashboard_framework_posture_uses_compact_two_row_tray() -> None:
    overview = (ROOT / "app/web/src/components/dashboard/ComplianceOverview.tsx").read_text(encoding="utf-8")

    assert "grid-rows-2" in overview
    assert "grid-flow-col" in overview
    assert "auto-cols-[104px]" in overview
    assert "h-[72px]" in overview
    assert "grid-cols-[30px_minmax(0,1fr)]" in overview
    assert "Framework families" in overview
    assert "catalog only" in overview
    assert "planned" in overview
    assert "overflow-x-auto" in overview
    assert 'aria-label="Framework posture comparison"' in overview
    assert ".slice(0, 6)" not in overview


def test_dashboard_compacts_the_score_ring_and_passes_the_framework_catalog() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")

    assert 'size="compact"' in dashboard
    assert "catalog={registeredFrameworks.data ?? []}" in dashboard


def test_dashboard_readiness_cards_keep_framework_marks_legible() -> None:
    readiness = READINESS.read_text(encoding="utf-8")

    assert readiness.count("size={44}") == 2
    assert 'aria-label="Framework readiness cards"' in readiness


def test_dashboard_evidence_loop_keeps_stage_labels_readable() -> None:
    signal_flow = SIGNAL_FLOW.read_text(encoding="utf-8")

    assert 'aria-label="Evidence operating loop"' in signal_flow
    assert 'text-slate-300">' in signal_flow
    assert "font-medium text-slate-300" in signal_flow


def test_next_dev_keeps_runtime_output_inside_the_web_project() -> None:
    config = NEXT_CONFIG.read_text(encoding="utf-8")

    assert 'distDir: isDev ? ".next"' in config
    assert '"../../src/security_lakehouse/web/dist"' in config
