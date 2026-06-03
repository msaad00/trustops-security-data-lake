"""Transport-agnostic service layer for GRC write paths.

These services wrap the ``db`` repositories plus serialization so the same
business logic backs the FastAPI routes, the MCP server, and the SDK without
duplication. They take a SQLAlchemy session, a ``tenant_id``, and plain Python
params (never FastAPI/Starlette objects) and return plain dicts.

Errors are raised as small, transport-agnostic types — :class:`NotFound` and
:class:`ValidationError` — so non-HTTP callers (MCP/SDK/CLI) are not forced to
import or catch ``fastapi.HTTPException``. The HTTP boundary translates these
into 404/400 responses.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for transport-agnostic service errors."""


class NotFound(ServiceError):
    """Requested entity does not exist for this tenant."""


class ValidationError(ServiceError):
    """Caller-supplied input failed validation."""


__all__ = ["NotFound", "ServiceError", "ValidationError"]
