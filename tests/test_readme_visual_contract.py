"""README hero assets stay sharp, accessible, and wired into the product story."""

import json
from pathlib import Path
from xml.etree import ElementTree

from tools.render_readme_header import render_logo, render_open_graph, render_social_preview

from security_lakehouse.safeguards import coverage_by_framework

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSETS = (
    ROOT / "docs" / "images" / "trustops-capability-header.svg",
    ROOT / "docs" / "images" / "trustops-logo.svg",
    ROOT / "docs" / "images" / "trustops-readme-banner.svg",
    ROOT / "app" / "web" / "public" / "og" / "trustops-share.svg",
)


def test_readme_header_leads_with_the_product_and_live_build_status() -> None:
    readme = README.read_text(encoding="utf-8")
    header = readme.split("## One operating loop", maxsplit=1)[0]

    assert 'src="docs/images/trustops-capability-header.svg"' in header
    assert '<h1 align="center">Open evidence infrastructure for continuous GRC</h1>' in header
    assert '<h1 align="center">TrustOps</h1>' not in header
    assert "One self-hosted contract across Console · API · CLI · MCP · CI." in header
    assert "Quick start" in header
    assert "ci.yml?branch=main&amp;label=Build" in header
    assert header.index("trustops-capability-header.svg") < header.index("<h1")


def test_readme_hero_names_only_shipped_capabilities() -> None:
    root = ElementTree.parse(ASSETS[0]).getroot()
    copy = " ".join(text.strip() for text in root.itertext() if text.strip())
    coverage = coverage_by_framework()

    assert "Collect. Evaluate. Operate. Prove." in copy
    assert "Trust Data Lake" in copy
    assert "Read-only evidence" in copy
    assert "deterministic controls" in copy
    assert "governed findings" in copy
    assert "immutable proof" in copy
    assert f"{coverage['safeguards']} safeguards · {coverage['controls']} catalogued requirements" in copy
    assert f"{len(coverage['frameworks'])} framework packs" in copy
    assert "Console · API · CLI · MCP · CI" in copy
    source_ids = {
        "AWS": "aws-posture",
        "Azure": "azure-posture",
        "GCP": "gcp-posture",
        "GitHub": "github-security",
        "GitLab": "gitlab-security",
        "Okta": "okta-identity",
        "Snowflake": "snowflake-evidence-lake",
        "ClickHouse": "clickhouse-telemetry-lake",
    }
    connector_payload = json.loads((ROOT / "connectors" / "catalog.json").read_text(encoding="utf-8"))
    connectors = {entry["connector_id"]: entry for entry in connector_payload["connectors"]}
    for source, connector_id in source_ids.items():
        assert source in copy
        assert connectors[connector_id]["is_implemented"] is True
        assert connectors[connector_id]["collection_mode"] in {"direct_api_read", "existing_lake_read"}
    for framework in (
        "SOC 2",
        "ISO 27001",
        "FedRAMP",
        "CMMC",
        "NIST CSF",
        "CIS AWS",
        "HIPAA",
        "PCI DSS",
        "GDPR",
        "EU AI Act",
        "ISO 27017",
        "ISO 42001",
        "NIST AI RMF",
    ):
        assert framework in copy


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


def test_readme_hero_matches_the_deterministic_renderer() -> None:
    assert ASSETS[0].read_text(encoding="utf-8") == render_social_preview()


def test_readme_logo_matches_the_deterministic_renderer() -> None:
    assert ASSETS[1].read_text(encoding="utf-8") == render_logo()


def test_open_graph_image_matches_the_deterministic_renderer() -> None:
    assert ASSETS[3].read_text(encoding="utf-8") == render_open_graph()


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


def test_product_preview_leads_with_current_operator_surfaces() -> None:
    readme = README.read_text(encoding="utf-8")
    preview = readme.split("## Product preview", maxsplit=1)[1]
    preview = preview.split("\n## ", maxsplit=1)[0]

    for label, image in (
        ("Assessment overview", "trustops-demo-dashboard.png"),
        ("Framework coverage", "trustops-demo-frameworks.png"),
        ("Evidence", "trustops-demo-evidence.png"),
        ("Connectors", "trustops-demo-connectors.png"),
    ):
        assert label in preview
        assert image in preview

    assert "TrustOps" not in preview
    assert "audit room" in preview.lower()
