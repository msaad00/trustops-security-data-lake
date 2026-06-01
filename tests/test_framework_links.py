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


def test_iso42001_operational_control_maps_to_clause_8_1() -> None:
    # Clause 8.2 is "AI risk assessment" and 8.4 is "AI system impact assessment";
    # the operational-controls control must map to 8.1 "Operational planning and control".
    mappings = json.loads(Path("mappings/control_articles.json").read_text())
    rows = mappings.get("mappings", mappings)
    iso = next(r for r in rows if r["control_id"] == "ISO42001-8.1")
    article = iso["articles"][0]
    assert article["article_id"] == "8.1"
    assert article["title"] == "Operational planning and control"

    catalog = json.loads(Path("controls/catalog.json").read_text())
    controls = catalog.get("controls", catalog)
    assert any(c["control_id"] == "ISO42001-8.1" for c in controls)
    assert not any(c["control_id"] == "ISO42001-8.2" for c in controls)
