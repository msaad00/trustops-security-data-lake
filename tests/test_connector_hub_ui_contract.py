"""Regression contract for the concise connector hub experience."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
PAGE = ROOT / "app/web/src/app/connectors/page.tsx"


def test_connector_hub_uses_compact_interactive_filters_and_grid() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert 'aria-label="Connection view"' in page
    assert 'aria-label="Runner filter"' in page
    assert 'aria-label="Category filter"' in page
    assert "overflow-x-auto" in page
    assert 'className="grid gap-2 p-4 pt-0 lg:grid-cols-2"' in page
    assert "Needs attention" in page
    assert "Needs setup" in page
    assert "All categories" in page
    assert 'label: "Prove"' in page
    assert "raw collection evidence and evaluated gold reports" in page
