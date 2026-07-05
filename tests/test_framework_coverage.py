from __future__ import annotations

import json

from security_lakehouse.cli import main
from security_lakehouse.framework_coverage import (
    build_control_asset_applicability,
    build_framework_coverage,
    framework_coverage_summary,
    render_framework_coverage_markdown,
)


def test_framework_coverage_ledger_counts_seeded_mappings(capsys) -> None:
    rows = build_framework_coverage()
    applicability = build_control_asset_applicability()
    summary = framework_coverage_summary(rows, applicability)

    assert summary["framework_count"] == 13
    assert summary["implemented_framework_count"] == 10
    assert summary["planned_framework_count"] == 3
    assert summary["seeded_control_count"] == 635
    assert summary["reviewed_mapping_count"] == 635
    assert summary["missing_mapping_count"] == 0
    assert summary["seeded_mapping_coverage_pct"] == 100.0
    assert summary["asset_type_count"] == 18
    assert summary["control_asset_applicability_link_count"] == 2139
    assert summary["official_logo_count"] == 0
    assert summary["certification_seal_count"] == 0
    assert all(row["asset_policy"].startswith("neutral label") for row in rows)
    assert applicability[0] == {"asset_type": "service", "applicable_control_count": 480}

    assert main(["frameworks", "coverage"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["summary"] == summary
    assert out["applicability"] == applicability


def test_framework_coverage_markdown_is_source_linked_not_logo_based() -> None:
    markdown = render_framework_coverage_markdown(build_framework_coverage(), build_control_asset_applicability())

    assert "Seeded mapping coverage: 100.0%" in markdown
    assert "Asset types modeled: 18" in markdown
    assert "Control-to-asset applicability links: 2139" in markdown
    assert "## Control-To-Asset Applicability" in markdown
    assert "| `service` | 480 |" in markdown
    assert "Official source" in markdown
    assert "official logo" not in markdown.lower()
    assert "certification seal" not in markdown.lower()
    assert "EUR-Lex - Regulation (EU) 2016/679" in markdown
