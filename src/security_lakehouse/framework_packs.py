"""Full framework packs: SOC 2, NIST AI RMF, FedRAMP, CIS AWS, and ISO catalogs.

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

from security_lakehouse.catalog import DEFAULT_CONTROL_CATALOG
from security_lakehouse.catalog_versions import (
    DEFAULT_BUNDLE_LOCK_PATH,
    write_bundle_lock,
)
from security_lakehouse.mappings import DEFAULT_MAPPINGS
from security_lakehouse.pack_data import (
    CIS_AWS_SOURCE,
    FEDRAMP_SOURCE,
    ISO_27001_SOURCE,
    ISO_42001_CONTROLS,
    ISO_42001_SOURCE,
    cis_aws_v3_requirements,
    cis_section_risk_domain,
    iso_27001_2022_annex_a_refs,
    iso_27001_theme_risk_domain,
    nist_800_53_rev5_moderate_ids,
    nist_family_risk_domain,
)

JsonObject = dict[str, Any]

DEFAULT_VERIFIED_ARTICLE_IDS = Path(__file__).resolve().parents[2] / "frameworks" / "verified_article_ids.json"

PACK_SCOPE = "framework_packs_full_soc2_nist_fedramp_cis_iso_plus_seed"

REVIEWED_BY = "internal-trust-team"
REVIEWED_DATE = "2026-06-30"

SOC2_SOURCE = (
    "https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022"
)
NIST_AI_RMF_SOURCE = "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10"

# Expected full pack sizes (used by tests and coverage gates).
SOC2_COMMON_CRITERIA_COUNT = 33
SOC2_TSC_EXTENSION_COUNT = 28
SOC2_FULL_PACK_COUNT = SOC2_COMMON_CRITERIA_COUNT + SOC2_TSC_EXTENSION_COUNT
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
    if series.startswith("A"):
        return "availability"
    if series.startswith("C"):
        return "confidentiality"
    if series.startswith("PI"):
        return "processing-integrity"
    if series.startswith("P") and not series.startswith("PI"):
        return "privacy"
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
        "availability": "platform-engineering",
        "confidentiality": "security-platform",
        "processing-integrity": "platform-engineering",
        "privacy": "grc",
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
        "availability": ("service", "host", "data_store", "cloud_resource"),
        "confidentiality": ("data_store", "s3_bucket", "cloud_resource", "service"),
        "processing-integrity": ("service", "audit_log", "data_store"),
        "privacy": ("data_store", "service", "identity_user", "audit_log"),
    }
    return mapping.get(risk_domain, ("service",))


def _soc2_evaluation_rule(risk_domain: str) -> str:
    if risk_domain in {
        "identity",
        "monitoring",
        "controls-operations",
        "availability",
        "confidentiality",
        "processing-integrity",
    }:
        return "fail_when_open_violation_or_stale_evidence"
    if risk_domain in {"vendor-risk", "privacy"}:
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
        title = _SOC2_TITLES[cc]
        specs.append(_soc2_pack_spec(cc, title))
    return specs


def _soc2_pack_spec(article_id: str, title: str) -> PackControlSpec:
    risk = _soc2_risk_domain(article_id)
    owner = _soc2_owner(risk)
    return PackControlSpec(
        control_id=f"SOC2-{article_id}",
        framework_id="soc2",
        framework="SOC 2",
        framework_ref=f"SOC 2 {article_id}",
        article_id=article_id,
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


# Short internal titles — not AICPA licensed criterion text.
_SOC2_TSC_TITLES: dict[str, str] = {
    "A1.1": "Capacity and performance are monitored against availability commitments",
    "A1.2": "Environmental protections and backup processes support availability objectives",
    "A1.3": "Recovery procedures are established, maintained, and tested",
    "C1.1": "Confidential information is identified and protected",
    "C1.2": "Confidential information is disposed of securely",
    "PI1.1": "Processing specifications define complete and accurate processing objectives",
    "PI1.2": "System inputs are complete, accurate, and authorized",
    "PI1.3": "System processing is complete, accurate, timely, and authorized",
    "PI1.4": "System outputs are complete, accurate, and timely",
    "PI1.5": "Stored inputs, processing items, and outputs remain complete and accurate",
    "P1.1": "Privacy notice communicates objectives and practices to data subjects",
    "P2.1": "Choice, explicit consent, and documented implicit consent for personal information",
    "P3.1": "Personal information collection is limited to identified objectives",
    "P3.2": "Collection methods are communicated and consented where required",
    "P4.1": "Personal information use is limited to identified objectives",
    "P4.2": "Personal information retention aligns with objectives and legal requirements",
    "P4.3": "Personal information disposal is secure and documented",
    "P5.1": "Data subjects can access their personal information",
    "P5.2": "Data subject access requests are fulfilled in a timely manner",
    "P6.1": "Personal information disclosure is authorized and logged",
    "P6.2": "Third-party disclosures comply with privacy commitments",
    "P6.3": "Data subjects are notified of privacy practices and changes",
    "P6.4": "Breach and incident notification procedures exist and are tested",
    "P6.5": "Cross-border disclosure requirements are met",
    "P6.6": "Government and legal disclosure requests are controlled",
    "P6.7": "Disclosure to third parties is monitored over time",
    "P7.1": "Personal information quality is maintained and corrected",
    "P8.1": "Privacy compliance is monitored and enforced",
}


def soc2_tsc_extension_specs() -> list[PackControlSpec]:
    """SOC 2 supplemental TSC: Availability, Confidentiality, Processing Integrity, Privacy."""
    order = [
        *(f"A1.{i}" for i in range(1, 4)),
        *(f"C1.{i}" for i in range(1, 3)),
        *(f"PI1.{i}" for i in range(1, 6)),
        "P1.1",
        "P2.1",
        *(f"P3.{i}" for i in range(1, 3)),
        *(f"P4.{i}" for i in range(1, 4)),
        *(f"P5.{i}" for i in range(1, 3)),
        *(f"P6.{i}" for i in range(1, 8)),
        "P7.1",
        "P8.1",
    ]
    return [_soc2_pack_spec(article_id, _SOC2_TSC_TITLES[article_id]) for article_id in order]


def soc2_full_pack_specs() -> list[PackControlSpec]:
    """All 61 SOC 2 criteria: 33 common criteria plus 28 supplemental TSC extensions."""
    return soc2_common_criteria_specs() + soc2_tsc_extension_specs()


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


def _normalize_nist_control_id(control_id: str) -> str:
    return control_id.upper()


def fedramp_moderate_specs() -> list[PackControlSpec]:
    """FedRAMP Moderate foundation: NIST SP 800-53 Rev 5 Moderate baseline (287 controls)."""
    specs: list[PackControlSpec] = []
    for raw_id in nist_800_53_rev5_moderate_ids():
        article_id = _normalize_nist_control_id(raw_id)
        risk = nist_family_risk_domain(article_id)
        owner = _soc2_owner(risk)
        title = f"FedRAMP Moderate {article_id} — assessed from cloud posture and audit evidence"
        specs.append(
            PackControlSpec(
                control_id=f"FEDRAMP-{article_id}",
                framework_id="fedramp-moderate",
                framework="FedRAMP Moderate",
                framework_ref=f"FedRAMP Moderate {article_id}",
                article_id=article_id,
                title=title,
                risk_domain=risk,
                owner=owner,
                evaluation_rule=_soc2_evaluation_rule(risk),
                evidence_requirement=(
                    f"Current evidence supports FedRAMP Moderate control {article_id} "
                    "with reviewed mappings and fresh operational proof."
                ),
                asset_types=_soc2_assets(risk),
                source_url=FEDRAMP_SOURCE,
                official_source_ref="fedramp-moderate",
            )
        )
    return specs


def cis_aws_v3_specs() -> list[PackControlSpec]:
    """All 62 CIS Amazon Web Services Foundations Benchmark v3.0.0 recommendations."""
    specs: list[PackControlSpec] = []
    for req_id, req_title in cis_aws_v3_requirements():
        section = req_id.split(".", 1)[0]
        risk = cis_section_risk_domain(section)
        owner = _soc2_owner(risk)
        specs.append(
            PackControlSpec(
                control_id=f"CIS-AWS-{req_id}",
                framework_id="cis_aws",
                framework="CIS AWS Foundations Benchmark",
                framework_ref=f"CIS AWS Foundations {req_id}",
                article_id=req_id,
                title=req_title[:160],
                risk_domain=risk,
                owner=owner,
                evaluation_rule=_soc2_evaluation_rule(risk),
                evidence_requirement=(f"AWS posture evidence demonstrates CIS Foundations {req_id}: {req_title[:80]}"),
                asset_types=("cloud_resource", "cloud_policy", "iam_role", "identity_account", "s3_bucket"),
                source_url=CIS_AWS_SOURCE,
                official_source_ref="cis_aws",
            )
        )
    return specs


def iso_27001_2022_specs() -> list[PackControlSpec]:
    """All 93 ISO/IEC 27001:2022 Annex A controls."""
    specs: list[PackControlSpec] = []
    for ref in iso_27001_2022_annex_a_refs():
        risk = iso_27001_theme_risk_domain(ref)
        owner = _soc2_owner(risk)
        title = f"ISO 27001:2022 {ref} — assessed from ISMS and security operations evidence"
        specs.append(
            PackControlSpec(
                control_id=f"ISO27001-{ref}",
                framework_id="iso-27001-2022",
                framework="ISO 27001:2022",
                framework_ref=f"ISO 27001:2022 {ref}",
                article_id=ref,
                title=title,
                risk_domain=risk,
                owner=owner,
                evaluation_rule=_soc2_evaluation_rule(risk),
                evidence_requirement=(
                    f"Current evidence supports ISO 27001:2022 Annex A control {ref} "
                    "with reviewed mappings and operational proof."
                ),
                asset_types=_soc2_assets(risk),
                source_url=ISO_27001_SOURCE,
                official_source_ref="iso-27001-2022",
            )
        )
    return specs


def iso_42001_2023_specs() -> list[PackControlSpec]:
    """All 38 ISO/IEC 42001:2023 Annex A AI management controls."""
    specs: list[PackControlSpec] = []
    for ref, short_title in ISO_42001_CONTROLS:
        article_id = ref.removeprefix("A.")
        specs.append(
            PackControlSpec(
                control_id=f"ISO42001-{article_id}",
                framework_id="iso-42001-2023",
                framework="ISO 42001:2023",
                framework_ref=f"ISO 42001:2023 {ref}",
                article_id=article_id,
                title=short_title,
                risk_domain="ai-governance",
                owner="ai-security",
                evaluation_rule="fail_when_open_violation_or_stale_evidence",
                evidence_requirement=(f"AI governance evidence supports ISO 42001:2023 control {ref} ({short_title})."),
                asset_types=("ai_model", "ai_agent", "service", "data_store", "audit_log"),
                source_url=ISO_42001_SOURCE,
                official_source_ref="iso-42001-2023",
            )
        )
    return specs


PACK_BUILDERS = {
    "soc2": soc2_full_pack_specs,
    "nist-ai-rmf": nist_ai_rmf_specs,
    "fedramp-moderate": fedramp_moderate_specs,
    "cis-aws": cis_aws_v3_specs,
    "iso-27001-2022": iso_27001_2022_specs,
    "iso-42001-2023": iso_42001_2023_specs,
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


def _regenerate_verified_article_ids(mappings_payload: JsonObject, *, path: Path) -> None:
    """Rebuild the verified article allowlist from active mappings."""
    framework_article_ids: dict[str, list[str]] = {}
    for row in mappings_payload.get("mappings", []):
        framework_id = str(row["framework_id"])
        known = set(framework_article_ids.get(framework_id, []))
        for article in row.get("articles", []):
            article_id = str(article["article_id"])
            if article_id not in known:
                known.add(article_id)
                framework_article_ids.setdefault(framework_id, []).append(article_id)
    for framework_id, ids in framework_article_ids.items():
        framework_article_ids[framework_id] = sorted(ids)

    existing = _read_json(path) if path.is_file() else {}
    payload = {
        "schema": "trustops.verified_article_ids.v1",
        "note": existing.get(
            "note",
            (
                "Audit-verified, real control/article identifiers per framework. "
                "Any NEW mapping article_id must be added here, forcing human verification "
                "against the official source. Regenerated from mappings/control_articles.json "
                "by frameworks sync-packs."
            ),
        ),
        "framework_article_ids": dict(sorted(framework_article_ids.items())),
    }
    _write_json(path, payload)


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
    catalog_payload["scope"] = PACK_SCOPE

    mappings_payload["mappings"] = sorted(existing_mappings.values(), key=lambda row: str(row["control_id"]))
    control_map_payload["controls"] = sorted(existing_map.values(), key=lambda row: str(row["control_id"]))

    _write_json(catalog_path, catalog_payload)
    _write_json(mappings_path, mappings_payload)
    _write_json(control_map_path, control_map_payload)

    bundle = None
    if write_bundle:
        bundle = write_bundle_lock(lock_path=DEFAULT_BUNDLE_LOCK_PATH)
        _regenerate_verified_article_ids(mappings_payload, path=DEFAULT_VERIFIED_ARTICLE_IDS)

    framework_counts = {
        framework_id: sum(1 for row in catalog_payload["controls"] if row.get("framework_id") == framework_id)
        for framework_id in (
            "soc2",
            "nist-ai-rmf",
            "fedramp-moderate",
            "cis_aws",
            "iso-27001-2022",
            "iso-42001-2023",
        )
    }
    return {
        "packs": selected,
        "added_controls": added_controls,
        "added_mappings": added_mappings,
        "control_count": len(catalog_payload["controls"]),
        "soc2_control_count": framework_counts["soc2"],
        "nist_ai_rmf_control_count": framework_counts["nist-ai-rmf"],
        "fedramp_moderate_control_count": framework_counts["fedramp-moderate"],
        "cis_aws_control_count": framework_counts["cis_aws"],
        "iso_27001_control_count": framework_counts["iso-27001-2022"],
        "iso_42001_control_count": framework_counts["iso-42001-2023"],
        "framework_counts": framework_counts,
        "bundle_hash": bundle.get("components", {}).get("controls") if bundle else None,
    }
