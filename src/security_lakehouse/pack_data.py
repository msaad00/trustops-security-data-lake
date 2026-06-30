"""Static pack data for FedRAMP, CIS AWS, and ISO framework full packs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PACK_DATA_DIR = Path(__file__).resolve().parents[2] / "frameworks" / "packs" / "data"

FEDRAMP_MODERATE_COUNT = 287
CIS_AWS_V3_COUNT = 62
ISO_27001_2022_ANNEX_A_COUNT = 93
ISO_42001_2023_ANNEX_A_COUNT = 38

FEDRAMP_SOURCE = "https://csrc.nist.gov/publications/detail/sp/800-53b/final"
CIS_AWS_SOURCE = "https://www.cisecurity.org/benchmark/amazon_web_services"
ISO_27001_SOURCE = "https://www.iso.org/standard/27001"
ISO_42001_SOURCE = "https://www.iso.org/standard/42001"

ISO_42001_CONTROLS: tuple[tuple[str, str], ...] = (
    ("A.2.2", "AI policy"),
    ("A.2.3", "Alignment with other organizational policies"),
    ("A.2.4", "Review of the AI policy"),
    ("A.3.2", "AI roles and responsibilities"),
    ("A.3.3", "Reporting of concerns"),
    ("A.4.2", "Resource documentation"),
    ("A.4.3", "Data resources"),
    ("A.4.4", "Tooling resources"),
    ("A.4.5", "System and computing resources"),
    ("A.4.6", "Human resources"),
    ("A.5.2", "AI system impact assessment process"),
    ("A.5.3", "Documentation of AI system impact assessments"),
    ("A.5.4", "Assessing AI system impact on individuals or groups"),
    ("A.5.5", "Assessing societal impacts of AI systems"),
    ("A.6.1.2", "Objectives for responsible development of AI system"),
    ("A.6.1.3", "Processes for responsible design and development of AI systems"),
    ("A.6.2.2", "AI system requirements and specification"),
    ("A.6.2.3", "Documentation of AI system design and development"),
    ("A.6.2.4", "AI system verification and validation"),
    ("A.6.2.5", "AI system deployment"),
    ("A.6.2.6", "AI system operation and monitoring"),
    ("A.6.2.7", "AI system technical documentation"),
    ("A.6.2.8", "AI system recording of event logs"),
    ("A.7.2", "Data for development and enhancement of AI system"),
    ("A.7.3", "Acquisition of data"),
    ("A.7.4", "Quality of data for AI systems"),
    ("A.7.5", "Data provenance"),
    ("A.7.6", "Data preparation"),
    ("A.8.2", "System documentation and information for users"),
    ("A.8.3", "External reporting"),
    ("A.8.4", "Communication of incidents"),
    ("A.8.5", "Information for interested parties"),
    ("A.9.2", "Processes for responsible use of AI systems"),
    ("A.9.3", "Objectives for responsible use of AI system"),
    ("A.9.4", "Intended use of the AI system"),
    ("A.10.2", "Allocation of responsibilities"),
    ("A.10.3", "Suppliers"),
    ("A.10.4", "Customers"),
)


@lru_cache(maxsize=1)
def nist_800_53_rev5_moderate_ids() -> tuple[str, ...]:
    path = PACK_DATA_DIR / "nist_800_53_rev5_moderate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(str(row) for row in payload["control_ids"])


@lru_cache(maxsize=1)
def cis_aws_v3_requirements() -> tuple[tuple[str, str], ...]:
    path = PACK_DATA_DIR / "cis_aws_v3.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple((str(row["id"]), str(row["title"])) for row in payload["requirements"])


def iso_27001_2022_annex_a_refs() -> list[str]:
    refs: list[str] = []
    refs.extend(f"A.5.{index}" for index in range(1, 38))
    refs.extend(f"A.6.{index}" for index in range(1, 9))
    refs.extend(f"A.7.{index}" for index in range(1, 15))
    refs.extend(f"A.8.{index}" for index in range(1, 35))
    return refs


def nist_family_risk_domain(control_id: str) -> str:
    family = control_id.split("-")[0].upper()
    return {
        "AC": "identity",
        "AT": "governance",
        "AU": "monitoring",
        "CA": "risk-management",
        "CM": "controls-operations",
        "CP": "change-management",
        "IA": "identity",
        "IR": "monitoring",
        "MA": "controls-operations",
        "MP": "controls-operations",
        "PE": "change-management",
        "PL": "governance",
        "PM": "governance",
        "PS": "governance",
        "PT": "governance",
        "RA": "risk-management",
        "SA": "controls-operations",
        "SC": "controls-operations",
        "SI": "monitoring",
        "SR": "vendor-risk",
    }.get(family, "governance")


def iso_27001_theme_risk_domain(ref: str) -> str:
    if ref.startswith("A.5."):
        return "governance"
    if ref.startswith("A.6."):
        return "governance"
    if ref.startswith("A.7."):
        return "change-management"
    return "controls-operations"


def cis_section_risk_domain(section: str) -> str:
    return {
        "1": "identity",
        "2": "controls-operations",
        "3": "monitoring",
        "4": "monitoring",
        "5": "controls-operations",
    }.get(section, "controls-operations")
