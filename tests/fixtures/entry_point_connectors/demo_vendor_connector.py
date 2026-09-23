"""Synthetic third-party connector package, for testing entry-point loading.

This module stands in for what an external, separately-installed Python
package would ship: a single function implementing the
:data:`security_lakehouse.connector_runner.ConnectorBuilder` contract, which
its own ``pyproject.toml`` would register under the ``trustops.connectors``
entry-point group as::

    [project.entry-points."trustops.connectors"]
    demo-vendor-evidence = "demo_vendor_connector:build_demo_vendor"

It is not installed as a package; tests import it directly and monkeypatch
``importlib.metadata.entry_points`` to simulate discovery, so the loader
mechanics in ``connector_runner.effective_registry`` are exercised without
needing a real pip install in CI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from security_lakehouse.connector_runner import SyncInputs

CONNECTOR_ID = "demo-vendor-evidence"


def build_demo_vendor(inputs: SyncInputs) -> list[dict[str, Any]]:
    """Return a fixed evidence row, mirroring a fixture-backed collect_* call.

    A real third-party connector would branch on ``inputs.fixture_dir`` for a
    fixture client and on ``inputs.env``/``inputs.credentials`` for a live
    one, exactly like an in-repo adapter. This demo always returns the same
    schema-valid row so the loader test can assert on a stable shape.
    """
    collected_at = datetime.now(UTC).isoformat()
    return [
        {
            "event_id": "demo-vendor-evidence-1",
            "tenant_id": "demo-tenant",
            "event_time": collected_at,
            "source": "demo-vendor",
            "event_type": "demo.evidence",
            "entity": {"kind": "demo_resource", "id": "demo-resource-1"},
            "severity": "info",
            "attributes": {"fixture_dir": str(inputs.fixture_dir) if inputs.fixture_dir else None},
        }
    ]
