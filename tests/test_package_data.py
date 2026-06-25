"""Packaging contract for data catalogs used by installed CLI commands."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_wheel_data_files_include_runtime_catalogs() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = pyproject["tool"]["setuptools"]["data-files"]

    expected = {
        "connectors": ["connectors/catalog.json"],
        "controls": ["controls/bundle.lock.json", "controls/catalog.json"],
        "frameworks": ["frameworks/registry.json", "frameworks/verified_article_ids.json"],
        "mappings": ["mappings/control_articles.json", "mappings/control_map.json"],
        "programs": ["programs/catalog.json"],
    }
    assert data_files == expected

    for files in expected.values():
        for rel_path in files:
            assert (REPO_ROOT / rel_path).is_file(), rel_path
