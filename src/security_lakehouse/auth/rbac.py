"""Role-based access control: the role -> scope map and request identity."""

from __future__ import annotations

from dataclasses import dataclass

ROLE_SCOPES: dict[str, frozenset[str]] = {
    "admin": frozenset(
        {
            "read",
            "write",
            "snapshot",
            "auth_admin",
            "connector_manage",
            "workflow_manage",
            "control_manage",
            "evidence_request",
        }
    ),
    "security_admin": frozenset(
        {"read", "write", "snapshot", "connector_manage", "workflow_manage", "control_manage", "evidence_request"}
    ),
    "contributor": frozenset({"read", "write", "workflow_run", "evidence_request"}),
    "auditor": frozenset({"read"}),
    "read_only": frozenset({"read"}),
}


def scopes_for_role(role: str) -> frozenset[str]:
    """Scopes granted to a role; unknown roles get nothing."""
    return ROLE_SCOPES.get(role, frozenset())


@dataclass(frozen=True)
class Identity:
    """The authenticated principal resolved for a request."""

    user_id: str
    tenant_id: str
    email: str
    role: str
    scopes: frozenset[str]
    workspace_id: str | None = None
    api_key_id: str | None = None
    # Set when a commercial workspace's subscription has lapsed: scopes are
    # narrowed to reads until billing is fixed.
    billing_read_only: bool = False

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes
