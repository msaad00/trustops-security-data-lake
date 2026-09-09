"""The console must explain loading instead of rendering an empty canvas."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
QUERY_STATE = ROOT / "app/web/src/components/QueryState.tsx"
BRAND = ROOT / "app/web/src/lib/brand.ts"
TOP_BAR = ROOT / "app/web/src/components/shell/TopBar.tsx"


def test_loading_state_is_visible_and_branded() -> None:
    source = QUERY_STATE.read_text(encoding="utf-8")

    assert "TrustOpsMark" in source
    assert 'role="status"' in source
    assert "Loading" in source
    assert "security data lake" in source


def test_shell_surfaces_security_data_lake_positioning() -> None:
    brand = BRAND.read_text(encoding="utf-8")
    top_bar = TOP_BAR.read_text(encoding="utf-8")

    assert "trust layer for security data lakes" in brand
    assert "Normalize security evidence" in brand
    assert "subtitle={BRAND.consoleSubtitle}" in top_bar
