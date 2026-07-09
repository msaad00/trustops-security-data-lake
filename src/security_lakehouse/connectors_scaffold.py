"""Generate connector adapter starter files for the in-repo registry."""

from __future__ import annotations

import re
from pathlib import Path

_MODULE_TEMPLATE = '''"""{title} evidence collector (scaffold).

Replace this stub with a read-only collector that emits normalized raw events.
See docs/ADDING_CONNECTORS.md for the full contributor path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.models import utc_iso

CONNECTOR_ID = "{connector_id}"
DEFAULT_CONTROLS = ["SOC2-CC6.1"]


class {client_class}:
    """Live API client — read-only GET calls only."""


class {fixture_class}:
    """Offline fixture client backed by JSON under a fixture directory."""

    def __init__(self, fixture_dir: str | Path) -> None:
        self.fixture = Path(fixture_dir)


def collect_{slug}_evidence(
    client: {client_class} | {fixture_class},
    *,
    collected_at: datetime | None = None,
    tenant_id: str = "customer-managed",
    since: str | None = None,
) -> list[dict[str, Any]]:
    """Collect normalized raw evidence rows for ``{connector_id}``."""
    _ = client, collected_at, tenant_id, since
    raise NotImplementedError("implement collect_{slug}_evidence for {connector_id}")
'''

_TEST_TEMPLATE = '''"""Tests for the {connector_id} connector adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from security_lakehouse.connector_runner import has_adapter
from security_lakehouse.connectors_{slug} import collect_{slug}_evidence


def test_has_adapter_registered() -> None:
    assert has_adapter("{connector_id}") is True


@pytest.mark.skip(reason="replace fixture path after implementing the collector")
def test_collect_{slug}_evidence_fixture() -> None:
  fixture = Path(__file__).parent / "fixtures" / "{connector_id}"
  rows = collect_{slug}_evidence(None)  # type: ignore[arg-type]
  assert rows
'''


def _slugify(connector_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", connector_id.lower()).strip("_")


def _class_name(connector_id: str) -> str:
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", connector_id) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


def scaffold_connector(connector_id: str, *, title: str | None = None, output_dir: str | Path) -> dict[str, str]:
    """Write starter module + test files for a new connector adapter."""
    slug = _slugify(connector_id)
    if not slug:
        raise ValueError("connector_id must contain alphanumeric characters")
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    module_name = f"connectors_{slug}.py"
    test_name = f"test_{slug}_connector.py"
    client_class = f"{_class_name(connector_id)}Client"
    fixture_class = f"{_class_name(connector_id)}FixtureClient"
    context = {
        "connector_id": connector_id,
        "title": title or connector_id.replace("-", " ").title(),
        "slug": slug,
        "client_class": client_class,
        "fixture_class": fixture_class,
    }
    module_path = base / "src" / "security_lakehouse" / module_name
    test_path = base / "tests" / test_name
    module_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(_MODULE_TEMPLATE.format(**context), encoding="utf-8")
    test_path.write_text(_TEST_TEMPLATE.format(**context), encoding="utf-8")
    registry_line = f'    "{connector_id}": _build_{slug},'
    return {
        "module_path": str(module_path),
        "test_path": str(test_path),
        "registry_line": registry_line,
        "catalog_flag": '"is_implemented": true',
        "next_steps": (
            f"1. Implement collect_{slug}_evidence in {module_name}\n"
            f"2. Add _build_{slug} + REGISTRY entry in connector_runner.py\n"
            f"3. Set is_implemented: true on {connector_id} in connectors/catalog.json\n"
            f"4. Finish {test_name} and add tests/fixtures/{connector_id}/\n"
            "5. Document permissions in docs/CONNECTORS.md"
        ),
    }
