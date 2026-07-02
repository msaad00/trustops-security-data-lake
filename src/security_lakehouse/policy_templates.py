"""Bundled governance policy template catalog and rendering helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import _data_root, load_control_catalog

DEFAULT_POLICY_TEMPLATE_CATALOG = _data_root() / "policy_templates" / "catalog.json"
_VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def load_policy_template_catalog(path: str | Path | None = None) -> dict[str, Any]:
    catalog_path = Path(path or DEFAULT_POLICY_TEMPLATE_CATALOG)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    templates = payload.get("templates")
    if not isinstance(templates, list):
        raise ValueError("policy template catalog must contain a templates list")
    return payload


def list_policy_templates(path: str | Path | None = None) -> list[dict[str, Any]]:
    return list(load_policy_template_catalog(path).get("templates") or [])


def get_policy_template(template_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    for template in list_policy_templates(path):
        if str(template.get("template_id") or "") == template_id:
            return template
    return None


def validate_policy_template_catalog(path: str | Path | None = None) -> list[str]:
    errors: list[str] = []
    controls = load_control_catalog()
    seen: set[str] = set()
    for template in list_policy_templates(path):
        template_id = str(template.get("template_id") or "")
        if not template_id:
            errors.append("policy template missing template_id")
            continue
        if template_id in seen:
            errors.append(f"duplicate policy template_id {template_id}")
        seen.add(template_id)
        for control_id in template.get("related_control_ids") or []:
            if str(control_id) not in controls:
                errors.append(f"policy template {template_id} references unknown control {control_id}")
        body = str(template.get("body_markdown") or "")
        if not body.strip():
            errors.append(f"policy template {template_id} missing body_markdown")
    return errors


def render_policy_template(
    template: dict[str, Any],
    variables: dict[str, Any] | None = None,
) -> str:
    """Substitute ``{{variable}}`` placeholders in template markdown."""
    values = {str(key): str(value) for key, value in (variables or {}).items()}
    body = str(template.get("body_markdown") or "")

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return values.get(key, match.group(0))

    return _VARIABLE_RE.sub(_replace, body)
