"""Guards on framework source links and known control-mapping corrections.

These are deterministic/offline checks (no network) so CI catches a malformed or
known-dead official source link, and the ISO 42001 clause correction can't
regress.
"""

from __future__ import annotations

import json
from pathlib import Path

# Hosts known to be dead/misconfigured for the documents we cite. www.aicpa.com
# fails TLS (cert SAN does not cover it); the live host is www.aicpa-cima.com.
_DEAD_HOSTS = ("www.aicpa.com", "aicpa.com/resources")


def _iter_source_urls() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    registry = json.loads(Path("frameworks/registry.json").read_text())
    for fw in registry.get("frameworks", registry if isinstance(registry, list) else []):
        url = fw.get("official_source_url")
        if url:
            out.append((fw.get("framework_id", "?"), url))
    mappings = json.loads(Path("mappings/control_articles.json").read_text())
    rows = mappings.get("mappings", mappings if isinstance(mappings, list) else [])
    for row in rows:
        for article in row.get("articles", []):
            url = article.get("official_source_url")
            if url:
                out.append((f"{row.get('control_id', '?')}:{article.get('article_id')}", url))
    return out


def test_official_source_urls_are_https_and_not_dead() -> None:
    offenders = []
    for owner, url in _iter_source_urls():
        if not url.startswith("https://"):
            offenders.append(f"{owner}: not https ({url})")
        if any(dead in url for dead in _DEAD_HOSTS):
            offenders.append(f"{owner}: known-dead host ({url})")
    assert offenders == [], offenders


def test_iso42001_clause_8_1_and_annex_a_pack_controls() -> None:
    # Hand-authored ISO42001-8.1 maps to clause 8.1 (operational planning).
    # The full Annex A pack adds ISO42001-8.2 for A.8.2 — not clause 8.2.
    mappings = json.loads(Path("mappings/control_articles.json").read_text())
    rows = mappings.get("mappings", mappings)
    iso_81 = next(r for r in rows if r["control_id"] == "ISO42001-8.1")
    article = iso_81["articles"][0]
    assert article["article_id"] == "8.1"
    assert article["title"] == "Operational planning and control"

    iso_82 = next(r for r in rows if r["control_id"] == "ISO42001-8.2")
    annex = iso_82["articles"][0]
    assert annex["article_id"] == "8.2"
    assert annex["title"] == "System documentation and information for users"

    catalog = json.loads(Path("controls/catalog.json").read_text())
    controls = catalog.get("controls", catalog)
    control_ids = {c["control_id"] for c in controls}
    assert "ISO42001-8.1" in control_ids
    assert "ISO42001-8.2" in control_ids
