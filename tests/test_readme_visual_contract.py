"""README hero assets stay sharp, accessible, and wired into the product story."""

from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSETS = (
    ROOT / "docs" / "images" / "trustops-social-preview.svg",
    ROOT / "docs" / "images" / "trustops-logo.svg",
    ROOT / "docs" / "images" / "trustops-readme-banner.svg",
)


def test_readme_header_leads_with_the_product_and_live_build_status() -> None:
    readme = README.read_text(encoding="utf-8")
    header = readme.split("## One operating loop", maxsplit=1)[0]

    assert 'src="docs/images/trustops-social-preview.svg"' in header
    assert '<h1 align="center">TrustOps</h1>' in header
    assert "Read-only evidence. Deterministic controls. Audit-ready proof." in header
    assert "Quick start" in header
    assert "ci.yml?branch=main&amp;label=Build" in header
    assert header.index("trustops-social-preview.svg") < header.index("<h1")


def test_readme_visuals_are_accessible_scalable_svg_assets() -> None:
    for path in ASSETS:
        assert path.is_file(), f"README visual is missing: {path.relative_to(ROOT)}"
        root = ElementTree.parse(path).getroot()
        assert root.attrib.get("viewBox"), f"{path.name} needs a viewBox for crisp scaling"
        assert root.attrib.get("role") == "img"
        labelled_by = root.attrib.get("aria-labelledby", "").split()
        assert labelled_by == ["title", "desc"]

        children = {child.tag.rsplit("}", 1)[-1]: child for child in root}
        assert children["title"].text
        assert children["desc"].text


def test_operating_loop_banner_is_presented_with_the_matching_section() -> None:
    readme = README.read_text(encoding="utf-8")
    section = readme.split("## One operating loop", maxsplit=1)[1]
    before_next_section = section.split("\n## ", maxsplit=1)[0]

    assert 'src="docs/images/trustops-readme-banner.svg"' in before_next_section
    copy = before_next_section.lower()
    assert "collect" in copy
    assert "evaluate" in copy
    assert "operate" in copy
    assert "prove" in copy
