"""Regression contract for Koda shell branding scale."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
SHELL = ROOT / "app/web/src/components/shell/Shell.tsx"
SIDEBAR = ROOT / "app/web/src/components/shell/Sidebar.tsx"
TOPBAR = ROOT / "app/web/src/components/shell/TopBar.tsx"


def test_shell_koda_mark_is_prominent() -> None:
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    topbar = TOPBAR.read_text(encoding="utf-8")

    assert 'markSize="md"' in sidebar
    assert 'markSize="lg"' in topbar


def test_shell_uses_document_scroll_not_fixed_canvas() -> None:
    shell = SHELL.read_text(encoding="utf-8")
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    topbar = TOPBAR.read_text(encoding="utf-8")

    assert "flex min-h-dvh" in shell
    assert "flex h-dvh" not in shell
    assert "flex-col overflow-hidden bg-rail" not in shell
    assert 'id="main-content"' in shell
    assert "overflow-x-hidden" in shell
    assert "sticky top-0 z-40" in topbar
    assert "sticky top-[52px]" in sidebar
