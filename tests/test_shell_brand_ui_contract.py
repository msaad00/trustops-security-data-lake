"""Regression contract for Koda shell branding scale."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
SIDEBAR = ROOT / "app/web/src/components/shell/Sidebar.tsx"
TOPBAR = ROOT / "app/web/src/components/shell/TopBar.tsx"


def test_shell_koda_mark_is_prominent() -> None:
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    topbar = TOPBAR.read_text(encoding="utf-8")

    assert 'markSize="md"' in sidebar
    assert 'markSize="lg"' in topbar
