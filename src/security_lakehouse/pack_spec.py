"""Shared pack control spec type for full and limited framework packs."""

from __future__ import annotations

from dataclasses import dataclass


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
