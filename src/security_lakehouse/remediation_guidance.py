"""Per-control 'how to fix' remediation guidance.

A failing control test tells an owner *that* something is wrong; this resolves
*what to do about it*. Guidance is authored neutrally and keyed by a control's
risk domain (``mappings/remediation_guidance.json``), with a framework-agnostic
default so every control resolves to actionable steps even before its domain is
authored. A per-control override slot can be added later without changing callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from security_lakehouse.catalog import _data_root
from security_lakehouse.io import read_json

DEFAULT_GUIDANCE_PATH = _data_root() / "mappings" / "remediation_guidance.json"


def load_guidance(path: str | Path | None = None) -> dict[str, Any]:
    """Load the remediation-guidance catalog."""
    data = read_json(path or DEFAULT_GUIDANCE_PATH)
    if not isinstance(data, dict):
        raise ValueError("remediation guidance must be a JSON object")
    return data


def guidance_for_control(control: dict[str, Any], *, guidance: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve remediation guidance for a control (its risk domain, else default)."""
    data = guidance if guidance is not None else load_guidance()
    by_domain = data.get("by_risk_domain", {}) if isinstance(data.get("by_risk_domain"), dict) else {}
    domain = str(control.get("risk_domain") or "")
    matched = domain in by_domain
    entry = by_domain.get(domain) or data.get("default", {})
    if not isinstance(entry, dict):
        entry = {}
    return {
        "control_id": control.get("control_id"),
        "risk_domain": domain or None,
        "framework": control.get("framework"),
        "title": control.get("title"),
        "matched": matched,
        "summary": str(entry.get("summary", "")),
        "steps": [str(step) for step in entry.get("steps", [])],
        "references": [str(ref) for ref in entry.get("references", [])],
    }
