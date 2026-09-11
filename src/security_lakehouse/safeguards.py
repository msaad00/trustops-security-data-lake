"""Common Control Framework: safeguards as the operated object.

The control catalog is framework-first — 942 requirements, each carrying its own
``evidence_requirement``. Answering all of them means answering the same question
once per framework.

A safeguard inverts that. It is the thing an operator actually runs: one evidence
requirement, one evaluation rule, one owner. Framework requirements map *into* it,
many-to-one, and framework readiness is derived from safeguard posture rather than
computed alongside it.

The relationship is many-to-many in both directions, and deliberately so:

* one safeguard satisfies many requirements across frameworks — the point of a CCF
* one requirement may need several safeguards — SOC2 CC7.2 wants both detection
  and audit logging, so it is met only when *both* pass

That second case is why :func:`requirement_status` requires every mapped safeguard
to pass. Treating "any" as sufficient would let a passing logging safeguard report
a monitoring requirement as met.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import load_control_catalog

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAFEGUARDS = ROOT / "controls" / "safeguards.json"

SCHEMA = "trustops.safeguards.v1"
VALID_ROLES = {"primary", "equivalent"}
VALID_REVIEW_STATES = {"reviewed", "proposed"}

# These labels describe the operated CCF safeguard families, not official
# framework names. Keep the ids stable so the CLI, API, and console can join on
# the same family even when a safeguard title changes.
CCF_FAMILY_LABELS = {
    "identity": "Identity and access",
    "data-protection": "Data protection",
    "detection": "Detection",
    "logging": "Audit logging",
    "change-management": "Change management",
    "vulnerability-management": "Vulnerability management",
    "third-party-risk": "Third-party risk",
    "risk-management": "Risk management",
    "availability": "Availability and recovery",
    "ai-governance": "AI governance",
    "incident-response": "Incident response",
    "training": "Security awareness",
    "physical": "Physical security",
    "secure-development": "Secure development",
    "network": "Network security",
    "privacy-rights": "Privacy rights",
    "data-inventory": "Data inventory",
    "data-retention": "Data retention",
    "processing-integrity": "Processing integrity",
}

JsonObject = dict[str, Any]


def _validate_mapping_source(source: Any, *, context: str) -> list[str]:
    """Validate provenance for a published crosswalk mapping."""
    if not isinstance(source, dict):
        return [f"{context}: mapping_source must be an object"]

    problems: list[str] = []
    for field in ("name", "locator"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            problems.append(f"{context}: mapping_source.{field} must be a non-empty string")

    url = source.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        problems.append(f"{context}: mapping_source.url must use https")

    digest = source.get("sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        problems.append(f"{context}: mapping_source.sha256 must be 64 lowercase hexadecimal characters")
    return problems


def load_safeguards(path: str | Path | None = None) -> JsonObject:
    """Return the raw safeguards payload."""
    payload = json.loads(Path(path or DEFAULT_SAFEGUARDS).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("safeguards"), list):
        raise ValueError("safeguards file must contain a `safeguards` list")
    return payload


def validate_safeguards(payload: JsonObject, *, catalog: dict[str, Any] | None = None) -> list[str]:
    """Return a list of problems; empty means the CCF is internally consistent.

    Returns rather than raises so a caller can report every problem at once —
    a curation pass wants the whole list, not the first failure.
    """
    problems: list[str] = []
    if payload.get("schema") != SCHEMA:
        problems.append(f"schema must be {SCHEMA!r}, got {payload.get('schema')!r}")

    known = set(catalog if catalog is not None else load_control_catalog())
    seen_ids: set[str] = set()

    for entry in payload.get("safeguards", []):
        sid = entry.get("safeguard_id")
        if not sid:
            problems.append("a safeguard is missing safeguard_id")
            continue
        if sid in seen_ids:
            problems.append(f"{sid}: duplicate safeguard_id")
        seen_ids.add(sid)

        if not entry.get("asset_types"):
            problems.append(f"{sid}: missing asset_types — a safeguard must say what it applies to")

        for field in ("title", "risk_domain", "objective", "evidence_requirement", "evaluation_rule", "owner"):
            if not entry.get(field):
                problems.append(f"{sid}: missing {field}")

        if "mapping_source" in entry:
            problems.extend(_validate_mapping_source(entry["mapping_source"], context=str(sid)))

        satisfies = entry.get("satisfies")
        if not isinstance(satisfies, list) or not satisfies:
            problems.append(f"{sid}: must satisfy at least one framework requirement")
            continue

        primaries = [m for m in satisfies if m.get("role") == "primary"]
        if len(primaries) != 1:
            problems.append(f"{sid}: expected exactly one primary requirement, found {len(primaries)}")

        for member in satisfies:
            control_id = member.get("control_id")
            if control_id not in known:
                problems.append(f"{sid}: unknown control_id {control_id!r}")
            role = member.get("role", "equivalent")
            if role not in VALID_ROLES:
                problems.append(f"{sid}: invalid role {role!r} on {control_id!r}")
            review = member.get("review_status", "reviewed")
            if review not in VALID_REVIEW_STATES:
                problems.append(f"{sid}: invalid review_status {review!r} on {control_id!r}")
            if "mapping_source" in member:
                problems.extend(_validate_mapping_source(member["mapping_source"], context=f"{sid}/{control_id}"))

    return problems


def safeguards_by_requirement(
    payload: JsonObject | None = None, *, reviewed_only: bool = False
) -> dict[str, list[str]]:
    """Map each framework control_id to the safeguard ids that satisfy it.

    ``reviewed_only`` drops mappings a human has not confirmed. Attestation
    should use it; discovery and curation queues should not.
    """
    data = payload or load_safeguards()
    out: dict[str, list[str]] = {}
    for entry in data["safeguards"]:
        for member in entry.get("satisfies", []):
            if reviewed_only and member.get("review_status", "reviewed") != "reviewed":
                continue
            out.setdefault(str(member.get("control_id")), []).append(str(entry["safeguard_id"]))
    return out


def mapping_review_queue(
    payload: JsonObject | None = None,
    *,
    framework_id: str | None = None,
    risk_domain: str | None = None,
) -> list[JsonObject]:
    """Proposed (unreviewed) safeguard→requirement mappings awaiting expert sign-off.

    Read-only curation aid — it never promotes a mapping (that equivalence call is
    the reviewer's). Each item carries the ``reviewed_anchors`` already confirmed on
    the same safeguard, so a reviewer can judge a proposed equivalence against
    mappings they already trust and accept/reject fast. Source-backed items carry
    the published crosswalk provenance and exact locator. This is the backlog
    whose review grows the *attestable* coverage number.
    """
    data = payload or load_safeguards()
    items: list[JsonObject] = []
    for entry in data["safeguards"]:
        if risk_domain and str(entry.get("risk_domain")) != risk_domain:
            continue
        anchors = [
            str(member.get("control_id"))
            for member in entry.get("satisfies", [])
            if member.get("review_status", "reviewed") == "reviewed"
        ]
        for member in entry.get("satisfies", []):
            if member.get("review_status", "reviewed") == "reviewed":
                continue
            if framework_id and str(member.get("framework_id")) != framework_id:
                continue
            item: JsonObject = {
                "safeguard_id": str(entry["safeguard_id"]),
                "safeguard_title": entry.get("title"),
                "risk_domain": entry.get("risk_domain"),
                "control_id": str(member.get("control_id")),
                "framework_id": str(member.get("framework_id")),
                "role": member.get("role"),
                "reviewed_anchors": anchors,
            }
            source = member.get("mapping_source") if "mapping_source" in member else entry.get("mapping_source")
            if source is not None:
                item["mapping_source"] = source
            items.append(item)
    return items


def mapping_review_report(
    payload: JsonObject | None = None,
    *,
    framework_id: str | None = None,
    risk_domain: str | None = None,
) -> JsonObject:
    """Summarize the review backlog across frameworks and normalized domains."""
    items = mapping_review_queue(payload, framework_id=framework_id, risk_domain=risk_domain)
    sourced = [item for item in items if item.get("mapping_source")]
    unsourced = [item for item in items if not item.get("mapping_source")]

    def count_by(rows: list[JsonObject], field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in rows:
            value = str(item[field])
            counts[value] = counts.get(value, 0) + 1
        return dict(sorted(counts.items()))

    return {
        "proposed_mapping_count": len(items),
        "source_backed_mapping_count": len(sourced),
        "unsourced_mapping_count": len(unsourced),
        "by_framework": count_by(items, "framework_id"),
        "by_risk_domain": count_by(items, "risk_domain"),
        "source_backed_by_framework": count_by(sourced, "framework_id"),
        "unsourced_by_framework": count_by(unsourced, "framework_id"),
        "items": items,
    }


def requirement_status(control_id: str, safeguard_results: dict[str, str], payload: JsonObject | None = None) -> str:
    """Derive one framework requirement's status from its safeguards.

    ``unmapped`` when no safeguard claims it — distinct from ``fail``, because
    "we have not modelled this yet" and "we tested it and it failed" are different
    answers to an auditor.
    """
    mapped = safeguards_by_requirement(payload).get(control_id, [])
    if not mapped:
        return "unmapped"
    statuses = {safeguard_results.get(sid, "unknown") for sid in mapped}
    if "fail" in statuses:
        return "fail"
    if statuses == {"pass"}:
        return "pass"
    return "unknown"


def safeguards_for_asset_type(asset_type: str, payload: JsonObject | None = None) -> list[str]:
    """Safeguards that apply to an asset type.

    The catalog already records ``asset_types`` per requirement, and evaluation
    targets resources rather than frameworks — so a safeguard has to carry the
    union of what its requirements apply to, or the operated object cannot be
    pointed at anything.
    """
    data = payload or load_safeguards()
    return sorted(
        str(entry["safeguard_id"]) for entry in data["safeguards"] if asset_type in (entry.get("asset_types") or [])
    )


def coverage_by_family(payload: JsonObject | None = None) -> list[JsonObject]:
    """Report CCF coverage by operated safeguard family.

    A family is the safeguard's ``risk_domain``. This is deliberately separate
    from framework coverage: a family can touch several frameworks, and a
    proposed mapping makes a requirement evaluatable but not attestable. The
    ledger preserves both counts so the console can show breadth without
    overstating assurance.
    """
    data = payload or load_safeguards()
    grouped: dict[str, dict[str, Any]] = {}
    for entry in data["safeguards"]:
        family_id = str(entry.get("risk_domain") or "uncategorized")
        row = grouped.setdefault(
            family_id,
            {
                "family_id": family_id,
                "label": CCF_FAMILY_LABELS.get(family_id, family_id.replace("-", " ").title()),
                "safeguard_count": 0,
                "frameworks": set(),
                "control_ids": set(),
                "mapping_count": 0,
                "reviewed_mapping_count": 0,
                "proposed_mapping_count": 0,
            },
        )
        row["safeguard_count"] += 1
        for member in entry.get("satisfies", []):
            row["mapping_count"] += 1
            row["control_ids"].add(str(member.get("control_id")))
            framework_id = member.get("framework_id")
            if framework_id:
                row["frameworks"].add(str(framework_id))
            if member.get("review_status", "reviewed") == "reviewed":
                row["reviewed_mapping_count"] += 1
            else:
                row["proposed_mapping_count"] += 1

    rows: list[JsonObject] = []
    for family_id, row in sorted(grouped.items()):
        reviewed = int(row["reviewed_mapping_count"])
        rows.append(
            {
                "family_id": family_id,
                "label": row["label"],
                "safeguard_count": row["safeguard_count"],
                "framework_count": len(row["frameworks"]),
                "frameworks": sorted(row["frameworks"]),
                "mapped_requirement_count": len(row["control_ids"]),
                "mapping_count": row["mapping_count"],
                "reviewed_mapping_count": reviewed,
                "proposed_mapping_count": row["proposed_mapping_count"],
                "state": "reviewed" if reviewed else "proposed_only",
            }
        )
    return rows


def coverage_by_framework(payload: JsonObject | None = None, *, catalog: dict[str, Any] | None = None) -> JsonObject:
    """Report how much of each framework the CCF currently covers."""
    controls = catalog if catalog is not None else load_control_catalog()
    mapped = safeguards_by_requirement(payload)

    per_framework: dict[str, dict[str, int]] = {}
    for control_id, control in controls.items():
        framework = str(control.get("framework_id") or "unknown")
        row = per_framework.setdefault(framework, {"controls": 0, "covered": 0})
        row["controls"] += 1
        if control_id in mapped:
            row["covered"] += 1

    total = len(controls)
    covered = sum(1 for cid in controls if cid in mapped)
    reviewed_map = safeguards_by_requirement(payload, reviewed_only=True)
    reviewed = sum(1 for cid in controls if cid in reviewed_map)
    data = payload or load_safeguards()
    return {
        "safeguards": len(data["safeguards"]),
        "controls": total,
        "covered": covered,
        # Split so unconfirmed curation is never reported as attested coverage.
        "reviewed": reviewed,
        "proposed": covered - reviewed,
        "reviewed_pct": round(100.0 * reviewed / total, 1) if total else 0.0,
        "uncovered": total - covered,
        "coverage_pct": round(100.0 * covered / total, 1) if total else 0.0,
        "frameworks": {
            name: {
                **row,
                "coverage_pct": round(100.0 * row["covered"] / row["controls"], 1) if row["controls"] else 0.0,
            }
            for name, row in sorted(per_framework.items())
        },
        "families": coverage_by_family(data),
    }
