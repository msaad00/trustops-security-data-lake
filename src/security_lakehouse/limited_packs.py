"""Limited-mapping framework packs: GDPR, HIPAA, PCI DSS, EU AI Act.

Expands honest seed subsets toward managed-GRC breadth without claiming
full official catalog coverage. Each control maps to a single official article
or CFR section with short internal titles only.
"""

from __future__ import annotations

from collections.abc import Iterator

from security_lakehouse.framework_packs import PackControlSpec

GDPR_SOURCE = "https://eur-lex.europa.eu/eli/reg/2016/679/oj"
HIPAA_SOURCE = "https://www.hhs.gov/hipaa/for-professionals/security/index.html"
PCI_SOURCE = "https://www.pcisecuritystandards.org/document_library/?category=pcidss"
EU_AI_ACT_SOURCE = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689"

# (article_ref, title_suffix, risk_domain, owner, asset_types)
GDPR_ARTICLES: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("Art.5", "Processing principles evidenced", "privacy-engineering", "privacy-office", ("data_store", "service")),
    ("Art.6", "Lawful basis for processing documented", "privacy-engineering", "privacy-office", ("data_store",)),
    ("Art.7", "Consent conditions evidenced where used", "privacy-engineering", "privacy-office", ("service",)),
    ("Art.12", "Transparent privacy notices published", "privacy-engineering", "privacy-office", ("service",)),
    ("Art.13", "Collection-time privacy information provided", "privacy-engineering", "privacy-office", ("service",)),
    (
        "Art.14",
        "Indirect collection privacy information provided",
        "privacy-engineering",
        "privacy-office",
        ("service",),
    ),
    ("Art.15", "Data subject access rights supported", "privacy-engineering", "privacy-office", ("data_store",)),
    ("Art.17", "Erasure requests handled within SLA", "privacy-engineering", "privacy-office", ("data_store",)),
    ("Art.24", "Controller responsibility demonstrated", "governance", "privacy-office", ("service",)),
    ("Art.34", "Communication of breach to data subjects", "incident-response", "privacy-office", ("service",)),
    ("Art.37", "DPO designation evidenced where required", "governance", "privacy-office", ("service",)),
    (
        "Art.44",
        "Cross-border transfer safeguards documented",
        "data-protection",
        "privacy-office",
        ("data_store", "service"),
    ),
    ("Art.45", "Adequacy or transfer mechanism evidenced", "data-protection", "privacy-office", ("data_store",)),
    ("Art.46", "Standard contractual clauses or BCRs in place", "third-party-risk", "privacy-office", ("service",)),
)

HIPAA_SECTIONS: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("164.308(a)(2)", "Assigned security responsibility documented", "governance", "security-operations", ("service",)),
    (
        "164.308(a)(3)",
        "Workforce security procedures evidenced",
        "identity",
        "security-operations",
        ("user", "service"),
    ),
    ("164.308(a)(5)", "Security awareness training completed", "governance", "security-operations", ("user",)),
    ("164.308(a)(6)", "Security incident procedures tested", "incident-response", "security-operations", ("service",)),
    ("164.308(a)(7)", "Contingency plan and backups evidenced", "availability", "security-operations", ("data_store",)),
    ("164.308(a)(8)", "Periodic evaluation performed", "risk-management", "security-operations", ("service",)),
    ("164.308(b)", "Business associate agreements current", "third-party-risk", "security-operations", ("service",)),
    ("164.310(a)", "Facility access controls documented", "physical-security", "security-operations", ("service",)),
    ("164.312(a)", "Access control mechanisms enforced", "identity", "security-operations", ("user", "service")),
    ("164.312(c)", "Integrity controls for ePHI evidenced", "data-protection", "security-operations", ("data_store",)),
    ("164.314(a)", "Business associate requirements enforced", "third-party-risk", "security-operations", ("service",)),
    ("164.314(b)", "Group health plan requirements met", "governance", "security-operations", ("service",)),
)

PCI_REQUIREMENTS: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("1", "Network security controls enforced", "network-security", "security-operations", ("service", "network")),
    ("2", "Secure configurations applied", "configuration-management", "security-operations", ("service",)),
    ("3", "Stored account data protected", "data-protection", "security-operations", ("data_store",)),
    ("4", "Transmission encryption enforced", "data-protection", "security-operations", ("service", "network")),
    ("5", "Malicious software protections active", "malware-defense", "security-operations", ("service",)),
    ("6", "Secure development practices evidenced", "change-management", "engineering", ("repo", "service")),
    ("8", "User identification and authentication enforced", "identity", "security-operations", ("user",)),
    ("9", "Physical access to cardholder data restricted", "physical-security", "security-operations", ("service",)),
    ("12", "Information security policy maintained", "governance", "security-operations", ("service",)),
)

EU_AI_ACT_ARTICLES: tuple[tuple[str, str, str, str, tuple[str, ...]], ...] = (
    ("Art.5", "Prohibited AI practices not deployed", "ai-governance", "ai-security", ("ai_model", "ai_agent")),
    ("Art.6", "High-risk AI classification documented", "ai-governance", "ai-security", ("ai_model",)),
    ("Art.11", "Technical documentation maintained for high-risk AI", "ai-governance", "ai-security", ("ai_model",)),
    (
        "Art.17",
        "Quality management system for high-risk AI evidenced",
        "ai-governance",
        "ai-security",
        ("ai_model", "service"),
    ),
    ("Art.26", "Deployer obligations for high-risk AI met", "ai-governance", "ai-security", ("ai_model", "service")),
    ("Art.49", "Fundamental-rights impact assessment where required", "ai-governance", "privacy-office", ("ai_model",)),
    ("Art.51", "GPAI provider obligations evidenced", "ai-governance", "ai-security", ("ai_model",)),
    ("Art.71", "EU database registration where applicable", "ai-governance", "ai-security", ("ai_model",)),
    ("Art.72", "Post-market monitoring plan active", "ai-governance", "ai-security", ("ai_model", "ai_agent")),
)


def _limited_spec(
    *,
    control_id: str,
    framework_id: str,
    framework: str,
    framework_ref: str,
    article_id: str,
    title: str,
    risk_domain: str,
    owner: str,
    asset_types: tuple[str, ...],
    source_url: str,
) -> PackControlSpec:
    return PackControlSpec(
        control_id=control_id,
        framework_id=framework_id,
        framework=framework,
        framework_ref=framework_ref,
        article_id=article_id,
        title=title,
        risk_domain=risk_domain,
        owner=owner,
        evaluation_rule="fail_when_stale_evidence",
        evidence_requirement=f"Evidence for {framework_ref} exists within freshness SLA.",
        asset_types=asset_types,
        source_url=source_url,
        official_source_ref=framework_id,
    )


def gdpr_limited_pack_specs() -> Iterator[PackControlSpec]:
    for article_ref, title, domain, owner, assets in GDPR_ARTICLES:
        yield _limited_spec(
            control_id=f"GDPR-{article_ref}",
            framework_id="gdpr-2016-679",
            framework="GDPR",
            framework_ref=f"GDPR {article_ref}",
            article_id=article_ref,
            title=title,
            risk_domain=domain,
            owner=owner,
            asset_types=assets,
            source_url=GDPR_SOURCE,
        )


def hipaa_limited_pack_specs() -> Iterator[PackControlSpec]:
    for section, title, domain, owner, assets in HIPAA_SECTIONS:
        yield _limited_spec(
            control_id=f"HIPAA-{section}",
            framework_id="hipaa-security-rule",
            framework="HIPAA",
            framework_ref=f"45 CFR §{section}",
            article_id=section,
            title=title,
            risk_domain=domain,
            owner=owner,
            asset_types=assets,
            source_url=HIPAA_SOURCE,
        )


def pci_dss_limited_pack_specs() -> Iterator[PackControlSpec]:
    for req, title, domain, owner, assets in PCI_REQUIREMENTS:
        yield _limited_spec(
            control_id=f"PCI-DSS-{req}",
            framework_id="pci-dss-v4",
            framework="PCI DSS",
            framework_ref=f"PCI DSS v4 Req {req}",
            article_id=f"Req-{req}",
            title=title,
            risk_domain=domain,
            owner=owner,
            asset_types=assets,
            source_url=PCI_SOURCE,
        )


def eu_ai_act_limited_pack_specs() -> Iterator[PackControlSpec]:
    for article_ref, title, domain, owner, assets in EU_AI_ACT_ARTICLES:
        yield _limited_spec(
            control_id=f"EU-AI-ACT-{article_ref}",
            framework_id="eu-ai-act-2024-1689",
            framework="EU AI Act",
            framework_ref=f"EU AI Act {article_ref}",
            article_id=article_ref,
            title=title,
            risk_domain=domain,
            owner=owner,
            asset_types=assets,
            source_url=EU_AI_ACT_SOURCE,
        )


LIMITED_PACK_BUILDERS = {
    "gdpr": gdpr_limited_pack_specs,
    "hipaa": hipaa_limited_pack_specs,
    "pci-dss": pci_dss_limited_pack_specs,
    "eu-ai-act": eu_ai_act_limited_pack_specs,
}

# Expected minimum seeded counts after limited pack sync (existing + new).
LIMITED_PACK_MINIMUMS = {
    "gdpr-2016-679": 20,
    "hipaa-security-rule": 18,
    "pci-dss-v4": 12,
    "eu-ai-act-2024-1689": 15,
}
