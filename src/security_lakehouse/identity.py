"""Shared identity-type classification for cloud connectors.

Cloud identities split into *human* sign-in accounts and *non-human* service
identities. Several controls only apply to one kind — MFA, for example, is a
human console sign-in control, while a key-only service identity has no login
profile to protect. Connectors tag their identity evidence with an
``identity_type`` so evaluation can apply the right control per identity type.

The signals differ per provider, so this helper accepts whichever ones a given
connector has and normalizes them to a single vocabulary.
"""

from __future__ import annotations

HUMAN = "human"
SERVICE = "service"
UNKNOWN = "unknown"


def classify_identity_type(
    *,
    principal_type: str | None = None,
    member: str | None = None,
    console_access: bool | None = None,
) -> str:
    """Classify an identity as ``"human"``, ``"service"``, or ``"unknown"``.

    Signals, in priority order:

    * ``console_access`` (AWS): ``True`` => human, ``False`` => service.
    * ``principal_type`` (Azure): ``"User"`` => human;
      ``"ServicePrincipal"`` / ``"ManagedIdentity"`` => service; else unknown.
    * ``member`` (GCP IAM member string): ``user:`` => human;
      ``serviceAccount:`` => service; ``group:`` / other => unknown.

    The highest-priority signal that is provided wins; if none resolves the
    identity, the result is ``"unknown"``.
    """
    if console_access is not None:
        return HUMAN if console_access else SERVICE

    if principal_type is not None:
        normalized = principal_type.strip().lower()
        if normalized == "user":
            return HUMAN
        if normalized in {"serviceprincipal", "managedidentity"}:
            return SERVICE
        return UNKNOWN

    if member is not None:
        prefix = member.strip().lower()
        if prefix.startswith("user:"):
            return HUMAN
        if prefix.startswith("serviceaccount:"):
            return SERVICE
        return UNKNOWN

    return UNKNOWN
