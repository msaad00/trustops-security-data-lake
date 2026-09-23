"""A synthetic third-party connector that collides with a built-in connector_id.

Used to test that ``connector_runner.effective_registry`` never lets an
installed package shadow an in-repo adapter: the built-in must always win on
a connector_id collision, with a warning logged (never a silent overwrite,
never a crash).
"""

from __future__ import annotations

from typing import Any

from security_lakehouse.connector_runner import SyncInputs

# Deliberately the same connector_id as the built-in Okta identity adapter.
CONNECTOR_ID = "okta-identity"


def build_colliding_okta(inputs: SyncInputs) -> list[dict[str, Any]]:
    raise AssertionError("this third-party builder must never be called; the built-in should win")
