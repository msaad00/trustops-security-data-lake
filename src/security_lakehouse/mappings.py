"""Reviewed control_id ↔ source_article mappings.

Replaces the heuristic crosswalk with auditor-reviewed mappings. Each
mapping points from a local control_id to one or more articles in the
framework's official source, with reviewer attestation and rationale.

Loaded from ``mappings/control_articles.json``; readonly + validated.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import _data_root, load_control_catalog

ROOT = _data_root()
DEFAULT_MAPPINGS = ROOT / "mappings" / "control_articles.json"


def load_control_article_mappings(
    path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Return a {control_id: mapping_record} dict."""
    payload = json.loads(Path(path or DEFAULT_MAPPINGS).read_text(encoding="utf-8"))
    mappings = payload.get("mappings")
    if not isinstance(mappings, list):
        raise ValueError("control article mappings must contain a `mappings` list")
    out: dict[str, dict[str, Any]] = {}
    for mapping in mappings:
        cid = str(mapping.get("control_id") or "")
        if not cid:
            continue
        out[cid] = mapping
    return out


def validate_control_article_mappings(
    path: str | Path | None = None,
) -> list[str]:
    """Return errors for missing/invalid mapping fields."""
    errors: list[str] = []
    mappings = load_control_article_mappings(path)
    for cid, mapping in mappings.items():
        if not mapping.get("framework_id"):
            errors.append(f"mapping {cid} missing framework_id")
        articles = mapping.get("articles") or []
        if not articles:
            errors.append(f"mapping {cid} has no articles")
        for article in articles:
            for required in ("article_id", "title", "official_source_url", "reviewed_by", "reviewed_at", "rationale"):
                if not str(article.get(required) or "").strip():
                    errors.append(f"mapping {cid} article missing {required}")
    return errors


def build_reviewed_crosswalk(
    mappings_path: str | Path | None = None,
    catalog_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compute a reviewed framework × framework crosswalk.

    The matrix cells list:
      * ``shared_domains``: ``risk_domain`` values both frameworks cover. This
        is the load-bearing cross-framework signal — article_id and control_id
        are framework-unique, so they only ever match on the diagonal, whereas
        ``risk_domain`` is the shared semantic axis that makes "answer once,
        satisfy many" visible (e.g. access-control coverage in SOC 2 and ISO).
      * ``shared_articles``: same article_id appearing in both frameworks'
        mapping tables (rare across frameworks, but supported).
      * ``shared_controls``: same control_id touching both frameworks
        (this matters if a control maps into multiple framework versions).
      * ``mapping_count`` / ``article_count`` / ``domain_count`` totals on the
        row header.
    """
    mappings = load_control_article_mappings(mappings_path)
    catalog = load_control_catalog(catalog_path)
    by_framework: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for cid, mapping in mappings.items():
        framework_id = str(mapping.get("framework_id") or "")
        if framework_id:
            by_framework[framework_id][cid] = mapping

    def domains_for(framework: str) -> set[str]:
        return {
            str(catalog[cid].get("risk_domain") or "")
            for cid in by_framework[framework]
            if cid in catalog and str(catalog[cid].get("risk_domain") or "")
        }

    frameworks = sorted(by_framework)
    matrix: list[dict[str, Any]] = []
    for left in frameworks:
        left_articles = {
            article["article_id"]
            for mapping in by_framework[left].values()
            for article in (mapping.get("articles") or [])
        }
        left_controls = set(by_framework[left])
        left_domains = domains_for(left)
        row: dict[str, Any] = {
            "framework_id": left,
            "mapping_count": len(by_framework[left]),
            "article_count": len(left_articles),
            "domain_count": len(left_domains),
            "cells": [],
        }
        for right in frameworks:
            right_articles = {
                article["article_id"]
                for mapping in by_framework[right].values()
                for article in (mapping.get("articles") or [])
            }
            right_controls = set(by_framework[right])
            right_domains = domains_for(right)
            row["cells"].append(
                {
                    "framework_id": right,
                    "is_self": left == right,
                    "shared_domains": sorted(left_domains & right_domains),
                    "shared_articles": sorted(left_articles & right_articles),
                    "shared_controls": sorted(left_controls & right_controls),
                }
            )
        matrix.append(row)
    return {"frameworks": frameworks, "matrix": matrix}
