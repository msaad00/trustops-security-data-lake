"""Mockup company fixtures + CLI loader.

Each company directory under ``mockup_companies/<name>/`` ships a
``raw/security_events.jsonl`` shaped like real connector output. The
``fixtures load`` CLI command pipes that raw evidence through the
existing ``pipeline run`` so the workbench can demo a realistic lake
without standing up real connectors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from security_lakehouse.catalog import _data_root

ROOT = _data_root()
FIXTURES_DIR = ROOT / "mockup_companies"


@dataclass(frozen=True)
class Fixture:
    company: str
    raw_path: Path
    event_count: int
    sources: list[str]
    controls: list[str]


def _summary(raw_path: Path) -> tuple[int, list[str], list[str]]:
    count = 0
    sources: set[str] = set()
    controls: set[str] = set()
    with raw_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if source := row.get("source"):
                sources.add(str(source))
            for control_id in row.get("controls") or []:
                controls.add(str(control_id))
    return count, sorted(sources), sorted(controls)


def list_fixtures(root: Path | None = None) -> list[Fixture]:
    base = root or FIXTURES_DIR
    if not base.is_dir():
        return []
    out: list[Fixture] = []
    for company_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        raw = company_dir / "raw" / "security_events.jsonl"
        if not raw.is_file():
            continue
        count, sources, controls = _summary(raw)
        out.append(
            Fixture(
                company=company_dir.name,
                raw_path=raw,
                event_count=count,
                sources=sources,
                controls=controls,
            )
        )
    return out


def find_fixture(company: str, root: Path | None = None) -> Fixture | None:
    for fixture in list_fixtures(root):
        if fixture.company == company:
            return fixture
    return None
