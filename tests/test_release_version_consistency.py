"""Release 0.2.16 must present one version across every shipped surface."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "0.2.16"
RELEASE_DATE = "2026-09-24"


def test_release_version_is_consistent_across_package_chart_and_console() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    chart = (ROOT / "deploy" / "helm" / "trustops" / "Chart.yaml").read_text(encoding="utf-8")
    brand = (ROOT / "app" / "web" / "src" / "lib" / "brand.ts").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    package = json.loads((ROOT / "app/web/package.json").read_text())
    lock = json.loads((ROOT / "app/web/package-lock.json").read_text())
    assert package["version"] == lock["version"] == lock["packages"][""]["version"] == RELEASE_VERSION
    assert pyproject["project"]["version"] == RELEASE_VERSION
    assert pyproject["tool"]["commitizen"]["version"] == RELEASE_VERSION
    assert re.search(rf"^version: {re.escape(RELEASE_VERSION)}$", chart, re.MULTILINE)
    assert re.search(rf'^appVersion: "{re.escape(RELEASE_VERSION)}"$', chart, re.MULTILINE)
    assert f'version: "{RELEASE_VERSION}"' in brand
    assert f"## {RELEASE_VERSION} - {RELEASE_DATE}" in changelog
    # Development after a release may add an Unreleased section without
    # changing the published package/chart/console version.
    if "## Unreleased" in changelog:
        assert changelog.index("## Unreleased") < changelog.index(f"## {RELEASE_VERSION} - {RELEASE_DATE}")
