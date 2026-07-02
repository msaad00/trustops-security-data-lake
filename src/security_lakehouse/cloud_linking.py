"""One-click AWS/Azure account linking for managed-GRC-style connector onboarding.

AWS linking issues a tenant-scoped external ID and a CloudFormation quick-create
URL against the read-only posture role template in ``deploy/aws/``. Azure linking
builds an admin-consent URL when ``TRUSTOPS_AZURE_LINK_CLIENT_ID`` is set.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from security_lakehouse.connector_state import append_config_event
from security_lakehouse.io import read_json, write_json
from security_lakehouse.models import utc_iso
from security_lakehouse.public_url import normalize_public_url

CLOUD_LINK_CONNECTORS = frozenset({"aws-posture", "azure-posture"})
AWS_ROLE_NAME_DEFAULT = "TrustOpsPostureReadOnlyRole"
AWS_TEMPLATE_REL = Path("deploy/aws/trustops-posture-readonly-role.yaml")
SESSIONS_FILE = Path("gold") / "connectors" / "cloud_link_sessions.json"
_LINK_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _sessions_path(lake_dir: str | Path) -> Path:
    return Path(lake_dir) / SESSIONS_FILE


def _load_sessions(lake_dir: str | Path) -> dict[str, Any]:
    path = _sessions_path(lake_dir)
    if not path.is_file():
        return {"sessions": {}}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {"sessions": {}}
    if not isinstance(payload, dict):
        return {"sessions": {}}
    sessions = payload.get("sessions")
    if not isinstance(sessions, dict):
        return {"sessions": {}}
    return {"sessions": sessions}


def _save_sessions(lake_dir: str | Path, payload: dict[str, Any]) -> None:
    path = _sessions_path(lake_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)


def _repo_template_path() -> Path:
    return Path(__file__).resolve().parents[2] / AWS_TEMPLATE_REL


def aws_template_bytes() -> bytes:
    """Return the packaged AWS CloudFormation template."""
    path = _repo_template_path()
    if not path.is_file():
        raise FileNotFoundError(f"AWS link template is missing: {path}")
    return path.read_bytes()


def _aws_trusted_principal() -> str:
    return str(os.environ.get("TRUSTOPS_AWS_LINK_PRINCIPAL") or "").strip()


def _azure_link_client_id() -> str:
    return str(os.environ.get("TRUSTOPS_AZURE_LINK_CLIENT_ID") or "").strip()


def _public_base(public_url: str | None) -> str | None:
    return normalize_public_url(public_url) or normalize_public_url(os.environ.get("TRUSTOPS_PUBLIC_URL"))


def aws_template_url(public_url: str | None) -> str | None:
    """Return a public HTTPS URL for the AWS template, when ``public_url`` is set."""
    base = _public_base(public_url)
    if not base:
        return None
    return f"{base}/api/v1/connectors/aws-posture/link/template.yaml"


def aws_quick_create_url(
    *,
    external_id: str,
    public_url: str | None,
    trusted_principal: str | None = None,
    role_name: str = AWS_ROLE_NAME_DEFAULT,
) -> str | None:
    """Build the AWS console quick-create URL, or ``None`` without a public template URL."""
    template = aws_template_url(public_url)
    if not template:
        return None
    principal = (trusted_principal or _aws_trusted_principal()).strip()
    if not principal:
        return None
    params = {
        "templateURL": template,
        "stackName": "TrustOpsPostureReadOnly",
        "param_TrustedPrincipalArn": principal,
        "param_ExternalId": external_id,
        "param_RoleName": role_name,
    }
    query = urlencode(params, quote_via=quote)
    return f"https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?{query}"


def azure_consent_url(*, session_id: str, public_url: str | None) -> str | None:
    """Return a Microsoft admin-consent URL when the link app client id is configured."""
    client_id = _azure_link_client_id()
    base = _public_base(public_url)
    if not client_id or not base:
        return None
    redirect_uri = f"{base}/api/v1/connectors/azure-posture/link/callback"
    params = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": session_id,
        }
    )
    return f"https://login.microsoftonline.com/common/adminconsent?{params}"


def normalize_link_session_id(session_id: str) -> str | None:
    """Return a callback-safe cloud-link session id, or ``None`` when invalid."""
    token = session_id.strip()
    if not token or not _LINK_SESSION_ID_RE.fullmatch(token):
        return None
    return token


def azure_callback_redirect(*, session_id: str, public_url: str | None) -> str:
    token = normalize_link_session_id(session_id)
    base = _public_base(public_url)
    if token is None:
        path = "/console/connectors/?connect=azure-posture"
        return f"{base}{path}" if base else path
    path = f"/console/connectors/?connect=azure-posture&link_session={quote(token)}"
    if base:
        return f"{base}{path}"
    return path


def issue_cloud_link_redirect_token(lake_dir: str | Path, *, session_id: str) -> str:
    """Create a server-owned token that the browser can use to complete linking.

    Azure returns the original ``state`` value to the callback. Even after
    validation, some static analyzers conservatively treat that value as
    user-controlled when it is echoed into a redirect URL. The console does not
    need the original state value; it only needs a token that resolves back to
    the pending session. Generate that token here so redirects carry only
    server-minted data.
    """

    token = normalize_link_session_id(session_id)
    if token is None:
        raise KeyError("cloud link session not found")
    store = _load_sessions(lake_dir)
    session = store["sessions"].get(token)
    if not isinstance(session, dict):
        raise KeyError("cloud link session not found")
    redirect_token = secrets.token_urlsafe(18)
    session["redirect_token"] = redirect_token
    session["redirect_token_issued_at"] = utc_iso(datetime.now(UTC))
    store["sessions"][token] = session
    _save_sessions(lake_dir, store)
    return redirect_token


def resolve_cloud_link_session_id(lake_dir: str | Path, session_id: str) -> str | None:
    """Resolve an original session id or browser redirect token to a session id."""

    token = normalize_link_session_id(session_id)
    if token is None:
        return None
    store = _load_sessions(lake_dir)
    if isinstance(store["sessions"].get(token), dict):
        return token
    for original_id, session in store["sessions"].items():
        if isinstance(session, dict) and session.get("redirect_token") == token:
            return str(original_id)
    return None


def start_cloud_link(
    lake_dir: str | Path,
    connector_id: str,
    *,
    tenant_id: str,
    public_url: str | None = None,
) -> dict[str, Any]:
    """Create a pending cloud-link session for ``connector_id``."""
    if connector_id not in CLOUD_LINK_CONNECTORS:
        raise ValueError(f"cloud linking is not supported for {connector_id}")
    session_id = secrets.token_urlsafe(18)
    external_id = secrets.token_urlsafe(24)
    trusted_principal = _aws_trusted_principal()
    role_name = AWS_ROLE_NAME_DEFAULT
    session: dict[str, Any] = {
        "session_id": session_id,
        "connector_id": connector_id,
        "tenant_id": tenant_id,
        "status": "pending",
        "created_at": utc_iso(datetime.now(UTC)),
        "external_id": external_id if connector_id == "aws-posture" else None,
        "role_name": role_name if connector_id == "aws-posture" else None,
        "trusted_principal": trusted_principal or None,
        "azure_tenant_id": None,
    }
    if connector_id == "aws-posture":
        session["quick_create_url"] = aws_quick_create_url(
            external_id=external_id,
            public_url=public_url,
            trusted_principal=trusted_principal,
            role_name=role_name,
        )
        session["template_url"] = aws_template_url(public_url)
        session["manual_template_path"] = str(AWS_TEMPLATE_REL)
    if connector_id == "azure-posture":
        session["consent_url"] = azure_consent_url(session_id=session_id, public_url=public_url)
    store = _load_sessions(lake_dir)
    store["sessions"][session_id] = session
    _save_sessions(lake_dir, store)
    return session


def get_cloud_link_session(lake_dir: str | Path, session_id: str) -> dict[str, Any] | None:
    token = resolve_cloud_link_session_id(lake_dir, session_id)
    if token is None:
        return None
    row = _load_sessions(lake_dir)["sessions"].get(token)
    return row if isinstance(row, dict) else None


def record_azure_consent(
    lake_dir: str | Path,
    *,
    session_id: str,
    azure_tenant_id: str,
    admin_consent: bool,
) -> dict[str, Any]:
    """Persist Azure admin-consent callback metadata on a link session."""
    token = normalize_link_session_id(session_id)
    if token is None:
        raise KeyError("cloud link session not found")
    store = _load_sessions(lake_dir)
    session = store["sessions"].get(token)
    if not isinstance(session, dict):
        raise KeyError("cloud link session not found")
    if session.get("connector_id") != "azure-posture":
        raise ValueError("session is not an Azure cloud-link session")
    session["azure_tenant_id"] = azure_tenant_id
    session["admin_consent"] = admin_consent
    session["status"] = "consented" if admin_consent else "consent_denied"
    session["consented_at"] = utc_iso(datetime.now(UTC))
    store["sessions"][token] = session
    _save_sessions(lake_dir, store)
    return session


def complete_cloud_link(
    lake_dir: str | Path,
    connector_id: str,
    *,
    session_id: str,
    actor: str,
    account_id: str | None = None,
    subscription_id: str | None = None,
) -> dict[str, Any]:
    """Finalize a cloud-link session by staging connector credentials."""
    token = resolve_cloud_link_session_id(lake_dir, session_id)
    if token is None:
        raise KeyError("cloud link session not found")
    session = get_cloud_link_session(lake_dir, token)
    if session is None:
        raise KeyError("cloud link session not found")
    if session.get("connector_id") != connector_id:
        raise ValueError("session connector mismatch")
    credentials: dict[str, Any]
    options: dict[str, Any] = {}
    if connector_id == "aws-posture":
        if not account_id or not str(account_id).strip().isdigit() or len(str(account_id).strip()) != 12:
            raise ValueError("account_id must be a 12-digit AWS account id")
        acct = str(account_id).strip()
        role_name = str(session.get("role_name") or AWS_ROLE_NAME_DEFAULT)
        credentials = {
            "account_id": acct,
            "external_id": str(session.get("external_id") or ""),
            "role_arn": f"arn:aws:iam::{acct}:role/{role_name}",
        }
    elif connector_id == "azure-posture":
        if not subscription_id or not str(subscription_id).strip():
            raise ValueError("subscription_id is required")
        credentials = {"subscription_id": str(subscription_id).strip()}
        azure_tenant = str(session.get("azure_tenant_id") or "").strip()
        if azure_tenant:
            options["azure_tenant_id"] = azure_tenant
    else:
        raise ValueError(f"cloud linking is not supported for {connector_id}")
    record = append_config_event(
        lake_dir,
        connector_id=connector_id,
        state="disabled",
        actor=actor,
        credentials=credentials,
        options=options,
    )
    store = _load_sessions(lake_dir)
    linked = store["sessions"].get(token)
    if isinstance(linked, dict):
        linked["status"] = "completed"
        linked["completed_at"] = utc_iso(datetime.now(UTC))
        linked["configure_event"] = record.get("occurred_at")
        store["sessions"][token] = linked
        _save_sessions(lake_dir, store)
    return {"session": linked or session, "configure": record}
