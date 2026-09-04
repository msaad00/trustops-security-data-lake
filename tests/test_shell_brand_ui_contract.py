"""Regression contract for Trust Data Lake shell branding scale."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
SHELL = ROOT / "app/web/src/components/shell/Shell.tsx"
SIDEBAR = ROOT / "app/web/src/components/shell/Sidebar.tsx"
TOPBAR = ROOT / "app/web/src/components/shell/TopBar.tsx"
MARK = ROOT / "app/web/src/components/brand/TrustOpsMark.tsx"
BRAND_DOC = ROOT / "docs/BRAND.md"


def test_shell_uses_one_prominent_product_lockup() -> None:
    sidebar = SIDEBAR.read_text(encoding="utf-8")
    topbar = TOPBAR.read_text(encoding="utf-8")

    assert 'markSize="lg"' in topbar
    assert "TrustOpsLogo" not in sidebar


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


def test_brand_mark_uses_lake_contours_not_letter_monogram() -> None:
    mark = MARK.read_text(encoding="utf-8")
    brand_doc = BRAND_DOC.read_text(encoding="utf-8")

    assert 'data-mark="source-types"' in mark
    assert 'data-mark="source-points"' not in mark
    assert 'data-mark="lake-contours"' in mark
    assert 'data-mark="source-to-lake"' not in mark
    assert "TDL monogram" not in brand_doc
