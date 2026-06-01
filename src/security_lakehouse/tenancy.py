"""Per-tenant lake resolution for server mode.

Server mode binds to a lake *root*. Each tenant's bronze/silver/gold evidence
lives under ``<root>/tenants/<tenant_id>`` so one authenticated tenant can never
read another tenant's compliance data.

A *flat* lake written directly at the root — which the CLI pipeline, the
``fixtures`` loader, and local demos all produce — is served, for backward
compatibility, only to the single tenant the deployment is bound to (see
:func:`resolve_bound_tenant`) and to no other. A second tenant always resolves
to its own ``tenants/<id>`` subtree, which starts empty rather than exposing the
bound tenant's data.
"""

from __future__ import annotations

from pathlib import Path

TENANTS_DIRNAME = "tenants"


def is_flat_lake(root: Path) -> bool:
    """True if ``root`` holds lake zones directly (a pre-tenant-scoping layout)."""
    return (root / "silver").is_dir() or (root / "manifest.json").is_file()


def tenant_lake(root: str | Path, tenant_id: str, *, bound_tenant: str | None) -> Path:
    """Resolve the lake directory ``tenant_id`` is allowed to read and write.

    Resolution order:

    1. ``<root>/tenants/<tenant_id>`` when that subtree exists (the multi-tenant
       layout — always isolated per tenant).
    2. ``<root>`` itself when ``tenant_id`` is the deployment's bound tenant and
       the root is a flat single-tenant lake (backward compatibility / demos).
    3. otherwise the (not-yet-created) ``<root>/tenants/<tenant_id>`` path, so an
       unprovisioned tenant reads an empty lake instead of another tenant's data.
    """
    root_path = Path(root)
    scoped = root_path / TENANTS_DIRNAME / tenant_id
    if scoped.exists():
        return scoped
    if bound_tenant is not None and tenant_id == bound_tenant and is_flat_lake(root_path):
        return root_path
    return scoped


def resolve_bound_tenant(root: str | Path, *, require_auth: bool, tenant_ids: list[str]) -> str | None:
    """Pick the single tenant allowed to use a flat root lake, or ``None``.

    - Insecure no-auth mode binds the flat lake to the synthetic ``insecure``
      tenant so local demos keep working.
    - Otherwise the flat lake is bound only when exactly one tenant exists; with
      zero or multiple tenants it is bound to nobody and every tenant reads its
      own ``tenants/<id>`` subtree (fail-closed — no shared data).
    """
    if not require_auth:
        return "insecure"
    if len(tenant_ids) == 1:
        return tenant_ids[0]
    return None
