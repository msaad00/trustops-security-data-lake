"""OpenID Connect SSO configuration and login completion.

Configuration is environment-driven so no secrets live in the repo. The HTTP
redirect/callback flow lives in :mod:`security_lakehouse.server_app`; the
provisioning + session-issuance logic lives here in :func:`complete_oidc_login`
so it is unit-testable without a live identity provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from security_lakehouse.db import repository
from security_lakehouse.db.models import User

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class OIDCConfig:
    """Resolved OIDC settings for one deployment."""

    issuer: str
    client_id: str
    client_secret: str
    tenant_slug: str = "default"
    auto_provision: bool = False
    default_role: str = "read_only"
    scopes: str = "openid email profile"

    @property
    def metadata_url(self) -> str:
        return f"{self.issuer.rstrip('/')}/.well-known/openid-configuration"


def load_oidc_config() -> OIDCConfig | None:
    """Build OIDC config from the environment, or ``None`` when not configured."""
    issuer = os.environ.get("TRUSTOPS_OIDC_ISSUER")
    client_id = os.environ.get("TRUSTOPS_OIDC_CLIENT_ID")
    client_secret = os.environ.get("TRUSTOPS_OIDC_CLIENT_SECRET")
    if not (issuer and client_id and client_secret):
        return None
    return OIDCConfig(
        issuer=issuer,
        client_id=client_id,
        client_secret=client_secret,
        tenant_slug=os.environ.get("TRUSTOPS_OIDC_TENANT_SLUG", "default"),
        auto_provision=os.environ.get("TRUSTOPS_OIDC_AUTO_PROVISION", "").lower() in _TRUTHY,
        default_role=os.environ.get("TRUSTOPS_OIDC_DEFAULT_ROLE", "read_only"),
    )


def build_oauth(config: OIDCConfig):
    """Register the OIDC client with authlib's Starlette integration."""
    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    oauth.register(
        name="oidc",
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=config.metadata_url,
        client_kwargs={"scope": config.scopes},
    )
    return oauth


class OIDCLoginError(Exception):
    """Raised when an SSO assertion cannot be turned into a local session."""


def complete_oidc_login(
    session: Session,
    *,
    config: OIDCConfig,
    email: str,
    email_verified: bool | None = None,
    idp: str = "oidc",
    now: datetime | None = None,
) -> tuple[User, str]:
    """Map a verified SSO email to a local user + browser session token.

    Raises :class:`OIDCLoginError` when the tenant is unknown, the email is not
    verified by the identity provider, or the user is not provisioned (and
    auto-provisioning is disabled).
    """
    if not email:
        raise OIDCLoginError("identity provider returned no email")
    if email_verified is not True:
        raise OIDCLoginError("identity provider email is not verified")
    tenant = repository.get_tenant_by_slug(session, slug=config.tenant_slug)
    if tenant is None:
        raise OIDCLoginError(f"OIDC tenant {config.tenant_slug!r} does not exist")
    user = repository.find_or_provision_user(
        session,
        tenant_id=tenant.id,
        email=email,
        auto_provision=config.auto_provision,
        default_role=config.default_role,
    )
    if user is None:
        raise OIDCLoginError(f"no provisioned user for {email!r} and auto-provisioning is disabled")
    if not user.is_active:
        raise OIDCLoginError(f"user {email!r} is disabled")
    _row, token = repository.create_user_session(session, tenant_id=tenant.id, user_id=user.id, idp=idp, now=now)
    return user, token
