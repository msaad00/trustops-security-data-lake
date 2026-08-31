"""Contracts for dependency auditing in CI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_dependency_audit_exports_every_installed_extra() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "uv sync --frozen --all-extras" in workflow
    assert "uv export --all-extras --no-emit-project" in workflow
