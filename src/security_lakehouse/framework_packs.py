"""Full framework packs: SOC 2 TSC common criteria and NIST AI RMF 1.0.

Packs define every official criterion/subcategory ID with short internal titles
(no licensed normative text). ``sync_framework_packs`` merges pack rows into the
active control catalog and reviewed mappings without removing other frameworks
or richer hand-authored control definitions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import DEFAULT_CONTROL_CATALOG, load_control_catalog
from security_lakehouse.catalog_versions import (
    DEFAULT_BUNDLE_LOCK_PATH,
    DEFAULT_CROSSWALK_PATH,
    write_bundle_lock,
)
from security_lakehouse.mappings import DEFAULT_MAPPINGS

JsonObject = dict[str, Any]

REVIEWED_BY = "internal-trust-team"
REVIEWED_DATE = "2026-06-30"

SOC2_SOURCE = "https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022"
NIST_AI_RMF_SOURCE = "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10"

# Expected full pack sizes (used by tests and coverage gates).
SOC2_COMMON_CRITERIA_COUNT = 33
NIST_AI_RMF_SUBCATEGORY_COUNT = 72


@dataclass(frozen=True)
class PackControlSpec:
    control_id: str
    framework_id: str
    framework: str
    framework_ref: str
    article_id: str
    title: str
    risk_domain: str
    owner: str
    evaluation_rule: str
    evidence_requirement: str
    asset_types: tuple[str, ...]
    source_url: str
    official_source_ref: str


def _soc2_risk_domain(cc: str) -> str:
    series = cc.split(".")[0]
    return {
        "CC1": "governance",
        "CC2": "governance",
        "CC3": "risk-management",
        "CC4": "risk-management",
        "CC5": "controls-operations",
        "CC6": "identity",
        "CC7": "monitoring",
        "CC8": "change-management",
        "CC9": "vendor-risk",
    }.get(series, "governance")


def _soc2_owner(risk_domain: str) -> str:
    return {
        "governance": "grc",
        "risk-management": "grc",
        "controls-operations": "security-platform",
        "identity": "security-platform",
        "monitoring": "detection-engineering",
        "change-management": "platform-engineering",
        "vendor-risk": "grc",
    }.get(risk_domain, "security-platform")


def _soc2_assets(risk_domain: str) -> tuple[str, ...]:
    mapping: dict[str, tuple[str, ...]] = {
        "governance": ("service", "audit_log"),
        "risk-management": ("service", "audit_log"),
        "controls-operations": ("cloud_policy", "cloud_resource", "service"),
        "identity": ("iam_role", "identity_user", "identity_group", "okta_user"),
        "monitoring": ("audit_log", "service", "host"),
        "change-management": ("repo", "service", "container_image"),
        "vendor-risk": ("service", "data_store"),
    }
    return mapping.get(risk_domain, ("service",))


def _soc2_evaluation_rule(risk_domain: str) -> str:
    if risk_domain in {"identity", "monitoring", "controls-operations"}:
        return "fail_when_open_violation_or_stale_evidence"
    if risk_domain == "vendor-risk":
        return "fail_when_high_severity_open"
    return "fail_when_missing_evidence"


# Short internal titles — not AICPA licensed criterion text.
_SOC2_TITLES: dict[str, str] = {
    "CC1.1": "Control environment demonstrates integrity and ethical values",
    "CC1.2": "Board independence and oversight of internal control",
    "CC1.3": "Management establishes structure, authority, and responsibility",
    "CC1.4": "Commitment to competence is demonstrated",
    "CC1.5": "Individuals are held accountable for internal control",
    "CC2.1": "Quality information supports internal control objectives",
    "CC2.2": "Internal control information is communicated internally",
    "CC2.3": "Control matters are communicated to external parties when required",
    "CC3.1": "Objectives are specified with sufficient clarity",
    "CC3.2": "Risk to objectives is identified and analyzed",
    "CC3.3": "Fraud risk is considered in risk assessment",
    "CC3.4": "Changes that affect internal control are identified and assessed",
    "CC4.1": "Ongoing and separate monitoring activities are performed",
    "CC4.2": "Control deficiencies are evaluated and communicated",
    "CC5.1": "Control activities are selected and developed",
    "CC5.2": "Technology general controls support objectives",
    "CC5.3": "Policies are deployed through procedures",
    "CC6.1": "Logical access controls are evaluated from identity and authorization evidence",
    "CC6.2": "User registration and authorization are controlled",
    "CC6.3": "Role-based access is provisioned and reviewed",
    "CC6.4": "Access is removed or adjusted on role change",
    "CC6.5": "Physical access to facilities and assets is restricted",
    "CC6.6": "External party access is authorized and monitored",
    "CC6.7": "Data transmission and movement are protected",
    "CC6.8": "Malware and endpoint protections are in place",
    "CC7.1": "Vulnerabilities are identified and remediated",
    "CC7.2": "Security monitoring controls are evaluated from runtime, audit, and detection evidence",
    "CC7.3": "Security events are analyzed to identify anomalies",
    "CC7.4": "Security incidents are responded to and contained",
    "CC7.5": "Recovery and continuity activities are defined and tested",
    "CC8.1": "Changes to infrastructure and software are authorized and tested",
    "CC9.1": "Vendor and partner risks are assessed before engagement",
    "CC9.2": "Vendor and partner relationships are monitored over time",
}


def soc2_common_criteria_specs() -> list[PackControlSpec]:
    """All 33 SOC 2 Trust Services Criteria common criteria (CC1–CC9)."""
    order = [
        *(f"CC1.{i}" for i in range(1, 6)),
        *(f"CC2.{i}" for i in range(1, 4)),
        *(f"CC3.{i}" for i in range(1, 5)),
        *(f"CC4.{i}" for i in range(1, 3)),
        *(f"CC5.{i}" for i in range(1, 4)),
        *(f"CC6.{i}" for i in range(1, 9)),
        *(f"CC7.{i}" for i in range(1, 6)),
        "CC8.1",
        *(f"CC9.{i}" for i in range(1, 3)),
    ]
    specs: list[PackControlSpec] = []
    for cc in order:
        risk = _soc2_risk_domain(cc)
        owner = _soc2_owner(risk)
        title = _SOC2_TITLES[cc]
        specs.append(
            PackControlSpec(
                control_id=f"SOC2-{cc}",
                framework_id="soc2",
                framework="SOC 2",
                framework_ref=f"SOC 2 {cc}",
                article_id=cc,
                title=title,
                risk_domain=risk,
                owner=owner,
                evaluation_rule=_soc2_evaluation_rule(risk),
                evidence_requirement=(
                    f"Current evidence demonstrates {title.lower()} with no open high-risk failure or stale proof."
                ),
                asset_types=_soc2_assets(risk),
                source_url=SOC2_SOURCE,
                official_source_ref="soc2",
            )
        )
    return specs


def _nist_function_blocks() -> list[tuple[str, list[tuple[int, int]]]]:
    return [
        ("GOVERN", [(1, 7), (2, 3), (3, 2), (4, 3), (5, 2), (6, 2)]),
        ("MAP", [(1, 6), (2, 3), (3, 5), (4, 2), (5, 2)]),
        ("MEASURE", [(1, 3), (2, 13), (3, 3), (4, 3)]),
        ("MANAGE", [(1, 4), (2, 4), (3, 2), (4, 3)]),
    ]


def _nist_title(func: str, category: int, sub: int) -> str:
    return f"NIST AI RMF {func} {category}.{sub} — assessed from AI governance and operational evidence"


def _nist_risk_domain(func: str) -> str:
    return {
        "GOVERN": "ai-governance",
        "MAP": "ai-governance",
        "MEASURE": "ai-risk",
        "MANAGE": "ai-risk",
    }.get(func, "ai-governance")


def nist_ai_rmf_specs() -> list[PackControlSpec]:
    """All 72 NIST AI RMF 1.0 subcategories across GOVERN, MAP, MEASURE, MANAGE."""
    specs: list[PackControlSpec] = []
    for func, blocks in _nist_function_blocks():
        risk = _nist_risk_domain(func)
        for category, count in blocks:
            for sub in range(1, count + 1):
                ref = f"{func}-{category}.{sub}"
                title = _nist_title(func, category, sub)
                specs.append(
                    PackControlSpec(
                        control_id=f"NIST-AI-RMF-{ref}",
                        framework_id="nist-ai-rmf",
                        framework="NIST AI RMF",
                        framework_ref=f"NIST AI RMF {ref}",
                        article_id=ref,
                        title=title,
                        risk_domain=risk,
                        owner="ai-security",
                        evaluation_rule="fail_when_open_violation_or_stale_evidence"
                        if risk == "ai-risk"
                        else "fail_when_missing_evidence",
                        evidence_requirement=(
                            f"Current AI governance evidence supports {ref} with reviewed mappings and fresh proof."
                        ),
                        asset_types=("ai_model", "ai_agent", "service", "data_store"),
                        source_url=NIST_AI_RMF_SOURCE,
                        official_source_ref="nist-ai-rmf",
                    )
                )
    return specs


PACK_BUILDERS = {
    "soc2": soc2_common_criteria_specs,
    "nist-ai-rmf": nist_ai_rmf_specs,
}


def pack_control_row(spec: PackControlSpec) -> JsonObject:
    return {
        "control_id": spec.control_id,
        "framework_id": spec.framework_id,
        "framework": spec.framework,
        "title": spec.title,
        "risk_domain": spec.risk_domain,
        "owner": spec.owner,
        "evidence_requirement": spec.evidence_requirement,
        "evaluation_rule": spec.evaluation_rule,
        "frequency": "continuous",
        "implementation_status": "implemented",
        "version": "1.0.0",
        "valid_from": REVIEWED_DATE,
        "valid_to": None,
        "supersedes": None,
        "superseded_by": None,
        "change_reason": "Framework pack sync",
        "lifecycle_status": "active",
        "official_source_ref": spec.official_source_ref,
        "framework_ref": spec.framework_ref,
        "source_url": spec.source_url,
        "mapping_rationale": f"Pack mapping: control identifier matches {spec.framework_ref} verbatim.",
        "reviewed_by": REVIEWED_BY,
        "reviewed_date": REVIEWED_DATE,
        "signal_source": "silver/normalized_events.jsonl",
        "asset_types": list(spec.asset_types),
    }


def pack_mapping_row(spec: PackControlSpec) -> JsonObject:
    return {
        "control_id": spec.control_id,
        "framework_id": spec.framework_id,
        "articles": [
            {
                "article_id": spec.article_id,
                "title": spec.title[:120],
                "official_source_url": spec.source_url,
                "reviewed_by": REVIEWED_BY,
                "reviewed_at": f"{REVIEWED_DATE}T00:00:00Z",
                "rationale": f"Pack mapping to {spec.framework_ref}.",
            }
        ],
    }


def pack_control_map_row(spec: PackControlSpec) -> JsonObject:
    return {
        "control_id": spec.control_id,
        "framework": spec.framework,
        "title": spec.title[:120],
        "risk_domain": spec.risk_domain,
        "owner": spec.owner,
    }


def _read_json(path: Path) -> JsonObject:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def sync_framework_packs(
    *,
    packs: list[str] | None = None,
    catalog_path: Path | None = None,
    mappings_path: Path | None = None,
    control_map_path: Path | None = None,
    write_bundle: bool = True,
) -> dict[str, Any]:
    """Merge selected packs into catalog artifacts. Preserves hand-authored rows."""
    selected = packs or list(PACK_BUILDERS.keys())
    catalog_path = catalog_path or DEFAULT_CONTROL_CATALOG
    mappings_path = mappings_path or DEFAULT_MAPPINGS
    control_map_path = control_map_path or DEFAULT_CONTROL_CATALOG.parent.parent / "mappings" / "control_map.json"

    catalog_payload = _read_json(catalog_path)
    mappings_payload = _read_json(mappings_path)
    control_map_payload = _read_json(control_map_path)

    existing_controls = {str(row["control_id"]): row for row in catalog_payload.get("controls", [])}
    existing_mappings = {str(row["control_id"]): row for row in mappings_payload.get("mappings", [])}
    existing_map = {str(row["control_id"]): row for row in control_map_payload.get("controls", [])}

    added_controls = 0
    added_mappings = 0
    for pack_id in selected:
        builder = PACK_BUILDERS.get(pack_id)
        if builder is None:
            raise ValueError(f"unknown pack {pack_id!r}; choose from {sorted(PACK_BUILDERS)}")
        for spec in builder():
            if spec.control_id not in existing_controls:
                existing_controls[spec.control_id] = pack_control_row(spec)
                added_controls += 1
            if spec.control_id not in existing_mappings:
                existing_mappings[spec.control_id] = pack_mapping_row(spec)
                added_mappings += 1
            if spec.control_id not in existing_map:
                existing_map[spec.control_id] = pack_control_map_row(spec)

    catalog_payload["controls"] = sorted(existing_controls.values(), key=lambda row: str(row["control_id"]))
    catalog_payload["catalog_version"] = REVIEWED_DATE
    catalog_payload["scope"] = "framework_packs_soc2_nist_ai_rmf_full_plus_seed"

    mappings_payload["mappings"] = sorted(existing_mappings.values(), key=lambda row: str(row["control_id"]))
    control_map_payload["controls"] = sorted(existing_map.values(), key=lambda row: str(row["control_id"]))

    _write_json(catalog_path, catalog_payload)
    _write_json(mappings_path, mappings_payload)
    _write_json(control_map_path, control_map_payload)

    bundle = None
    if write_bundle:
        bundle = write_bundle_lock(lock_path=DEFAULT_BUNDLE_LOCK_PATH)

    soc2_count = sum(1 for row in catalog_payload["controls"] if row.get("framework_id") == "soc2")
    nist_count = sum(1 for row in catalog_payload["controls"] if row.get("framework_id") == "nist-ai-rmf")
    return {
        "packs": selected,
        "added_controls": added_controls,
        "added_mappings": added_mappings,
        "control_count": len(catalog_payload["controls"]),
        "soc2_control_count": soc2_count,
        "nist_ai_rmf_control_count": nist_count,
        "bundle_hash": bundle.get("components", {}).get("controls") if bundle else None,
    }
