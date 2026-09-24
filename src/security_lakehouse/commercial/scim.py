"""SCIM 2.0 settings for commercial hosted tenants.

Provisioning lives in :mod:`security_lakehouse.commercial.scim_provision` and
the routes in :mod:`security_lakehouse.server_routes.routers.scim`; both return
501 unless the commercial hosted build enables SCIM.
"""

from __future__ import annotations

import os
from typing import Any

from security_lakehouse.commercial.email import commercial_hosted_enabled


def scim_enabled() -> bool:
    return commercial_hosted_enabled() and os.environ.get("TRUSTOPS_SCIM_ENABLED", "").lower() in {"1", "true", "yes"}


def scim_config() -> dict[str, Any]:
    """Return non-secret SCIM settings for operator dashboards."""
    return {
        "enabled": scim_enabled(),
        "base_path": "/api/v1/scim/v2",
        "supported": scim_enabled(),
        "note": (
            "SCIM uses per-tenant bearer tokens issued at /api/v1/platform/scim/tokens (SHA-256 hashed at rest). "
            "OSS/self-hosted returns 501 until TRUSTOPS_COMMERCIAL_HOSTED=1 and TRUSTOPS_SCIM_ENABLED=1."
        ),
    }


def scim_not_implemented_detail() -> str:
    return (
        "SCIM provisioning is a commercial hosted feature; enable TRUSTOPS_COMMERCIAL_HOSTED and TRUSTOPS_SCIM_ENABLED"
    )


__all__ = ["scim_config", "scim_enabled", "scim_not_implemented_detail"]
