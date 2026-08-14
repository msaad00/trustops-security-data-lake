"""Google Workspace identity-evidence collector.

An identity connector mirroring ``connectors_okta``. It collects read-only
identity governance signals from a Google Workspace (Cloud Identity) directory
— user access state, 2-step-verification (MFA) enrollment, and group
membership — and emits them in the lake's raw evidence shape so they flow
through the same validate -> write -> pipeline path the other runners use.

Two clients sit behind one interface, mirroring ``connectors_okta``:

* :class:`GoogleWorkspaceClient` — authenticated ``urllib`` reads against the
  Google Workspace Admin SDK Directory API with an OAuth bearer token in the
  ``Authorization`` header.
* :class:`GoogleWorkspaceFixtureClient` — reads ``users.json`` /
  ``groups.json`` / ``members.json`` from a fixture directory so collection is
  fully testable in CI without a live directory.

The collector is strictly read-only and least-privilege: it only ever issues
GET requests against the directory ``users``, ``groups``, and group
``members`` resources and never mutates directory state.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse import netguard
from security_lakehouse.ingestion import backoff
from security_lakehouse.ingestion.paginate import paginate
from security_lakehouse.io import read_json
from security_lakehouse.models import utc_iso

# Identity controls that exist in controls/catalog.json. Verified before wiring.
IDENTITY_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.5.15", "HIPAA-164.308(a)(4)"]
MFA_CONTROLS = ["SOC2-CC6.1", "HIPAA-164.308(a)(4)"]
GROUP_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.5.15"]

# Directory API base URL for the Admin SDK Directory resource.
DIRECTORY_API_BASE = "https://admin.googleapis.com/admin/directory/v1"

DEFAULT_TIMEOUT = 20
USER_PAGE_LIMIT = 200


class GoogleWorkspaceClient:
    """Authenticated, read-only Google Workspace Directory API client."""

    def __init__(
        self,
        customer_id: str,
        *,
        access_token: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.customer_id = customer_id
        self.access_token = access_token
        self.timeout = timeout
        # A stable, non-secret origin slug used for asset scoping / ids.
        self.org_url = f"google-workspace://{customer_id}"

    def users(self) -> list[dict[str, Any]]:
        customer = urllib.parse.quote(str(self.customer_id), safe="")
        url = f"{DIRECTORY_API_BASE}/users?customer={customer}&maxResults={USER_PAGE_LIMIT}"
        return self._json_collection(url, key="users")

    def groups(self) -> list[dict[str, Any]]:
        customer = urllib.parse.quote(str(self.customer_id), safe="")
        url = f"{DIRECTORY_API_BASE}/groups?customer={customer}&maxResults={USER_PAGE_LIMIT}"
        return self._json_collection(url, key="groups")

    def members(self, group_id: str) -> list[dict[str, Any]]:
        safe_id = urllib.parse.quote(str(group_id), safe="")
        url = f"{DIRECTORY_API_BASE}/groups/{safe_id}/members?maxResults={USER_PAGE_LIMIT}"
        return self._json_collection(url, key="members")

    def _json_collection(self, url: str, *, key: str) -> list[dict[str, Any]]:
        # The Directory API pages with nextPageToken; a single GET truncates a
        # real tenant at maxResults, so follow the cursor to the end. It also
        # rate-limits with HTTP 429 + Retry-After, so each page is fetched under
        # backoff. `paginate` supplies the loop and a runaway page cap.
        def fetch_page(page_token: str | None) -> dict[str, Any]:
            page_url = url if not page_token else f"{url}&pageToken={urllib.parse.quote(page_token)}"
            request = urllib.request.Request(
                page_url,
                headers={
                    "accept": "application/json",
                    "authorization": f"Bearer {self.access_token}",
                    "user-agent": "trustops-security-data-lake",
                },
            )

            def _fetch() -> Any:
                with netguard.open_public(request, timeout=self.timeout, label="google workspace api") as resp:
                    return json.loads(resp.read().decode("utf-8"))

            payload = backoff.http_retry(_fetch)
            if not isinstance(payload, dict):
                raise ValueError(f"Google Workspace returned non-object JSON for {page_url}")
            return payload

        def extract_items(page: dict[str, Any]) -> list[dict[str, Any]]:
            return [item for item in page.get(key, []) if isinstance(item, dict)]

        def next_cursor(page: dict[str, Any]) -> str | None:
            return str(page.get("nextPageToken") or "") or None

        return list(paginate(fetch_page, extract_items, next_cursor))


class GoogleWorkspaceFixtureClient:
    """Offline Google Workspace client backed by a fixture directory."""

    def __init__(
        self,
        fixture_dir: str | Path,
        *,
        customer_id: str = "C00fixture",
    ) -> None:
        self.fixture = Path(fixture_dir)
        self.customer_id = customer_id
        self.org_url = f"google-workspace://{customer_id}"

    def users(self) -> list[dict[str, Any]]:
        return self._read_list("users.json")

    def groups(self) -> list[dict[str, Any]]:
        return self._read_list("groups.json")

    def members(self, group_id: str) -> list[dict[str, Any]]:
        payload = self._read("members.json")
        if isinstance(payload, dict):
            items = payload.get(str(group_id), [])
            return [item for item in items if isinstance(item, dict)]
        # A flat list fixture: keep only members that name this group.
        return [item for item in payload if isinstance(item, dict) and str(item.get("groupId")) == str(group_id)]

    def _read(self, name: str) -> Any:
        path = self.fixture / name
        return read_json(path) if path.exists() else []

    def _read_list(self, name: str) -> list[dict[str, Any]]:
        payload = self._read(name)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []


def collect_google_workspace_evidence(
    client: GoogleWorkspaceClient | GoogleWorkspaceFixtureClient,
    *,
    collected_at: datetime | None = None,
    tenant_id: str = "customer-managed",
) -> list[dict[str, Any]]:
    """Collect normalized raw identity evidence from a Workspace directory.

    Emits, per collection:

    * one identity-access event per user (suspended/archived -> identity
      controls),
    * one MFA-enrollment event per user (2-step verification -> MFA controls),
    * one group-membership event per group (membership -> group controls).

    Every event passes :func:`security_lakehouse.validation.validate_raw_events`.
    """
    now = collected_at or datetime.now(UTC)
    org = _org_slug(client.org_url)
    rows: list[dict[str, Any]] = []

    for user in client.users():
        user_id = str(user.get("id") or "").strip()
        if not user_id:
            continue
        rows.append(_user_event(client.customer_id, org, user, now, tenant_id))
        rows.append(_mfa_event(client.customer_id, org, user_id, user, now, tenant_id))

    for group in client.groups():
        group_id = str(group.get("id") or "").strip()
        if not group_id:
            continue
        members = _safe_members(client, group_id)
        rows.append(_group_event(client.customer_id, org, group, members, now, tenant_id))

    return rows


def _user_event(
    customer_id: str,
    org: str,
    user: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any]:
    user_id = str(user["id"])
    suspended = bool(user.get("suspended"))
    archived = bool(user.get("archived"))
    active = not suspended and not archived
    primary_email = user.get("primaryEmail")
    evidence_ref = f"{DIRECTORY_API_BASE}/users/{user_id}"
    return _event(
        org=org,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="identity_access",
        event_type="google_workspace.identity.user_access",
        asset_id=f"google_workspace:user:{user_id}",
        asset_type="identity_account",
        controls=IDENTITY_CONTROLS,
        # Accounts that cannot authenticate are the noteworthy ones.
        status="observed" if active else "open",
        severity="info" if active else "low",
        evidence_ref=evidence_ref,
        attributes={
            "user_id": user_id,
            "primary_email": primary_email,
            "suspended": suspended,
            "archived": archived,
            "can_authenticate": active,
            "is_admin": bool(user.get("isAdmin")),
            "creation_time": user.get("creationTime"),
            "last_login_time": user.get("lastLoginTime"),
        },
    )


def _mfa_event(
    customer_id: str,
    org: str,
    user_id: str,
    user: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any]:
    enrolled = bool(user.get("isEnrolledIn2Sv"))
    enforced = bool(user.get("isEnforcedIn2Sv"))
    suspended = bool(user.get("suspended"))
    archived = bool(user.get("archived"))
    active = not suspended and not archived
    # An active account without 2-step verification is the finding to raise.
    needs_mfa = active and not enrolled
    evidence_ref = f"{DIRECTORY_API_BASE}/users/{user_id}"
    return _event(
        org=org,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="mfa_enrollment",
        event_type="google_workspace.identity.mfa_enrollment",
        asset_id=f"google_workspace:user:{user_id}",
        asset_type="identity_account",
        controls=MFA_CONTROLS,
        status="open" if needs_mfa else "pass",
        severity="high" if needs_mfa else "info",
        evidence_ref=evidence_ref,
        attributes={
            "user_id": user_id,
            "mfa_enrolled": enrolled,
            "mfa_enforced": enforced,
            "can_authenticate": active,
            "needs_mfa": needs_mfa,
        },
    )


def _group_event(
    customer_id: str,
    org: str,
    group: dict[str, Any],
    members: list[dict[str, Any]],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any]:
    group_id = str(group["id"])
    member_emails = sorted({str(m.get("email")) for m in members if m.get("email")})
    roles = sorted({str(m.get("role")).upper() for m in members if m.get("role")})
    # A group that grants elevated membership roles is worth surfacing.
    has_elevated = any(role in {"OWNER", "MANAGER"} for role in roles)
    evidence_ref = f"{DIRECTORY_API_BASE}/groups/{group_id}/members"
    return _event(
        org=org,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="group_membership",
        dedupe_key=group_id,
        event_type="google_workspace.identity.group_membership",
        asset_id=f"google_workspace:group:{group_id}",
        asset_type="identity_group",
        controls=GROUP_CONTROLS,
        status="open" if has_elevated else "observed",
        severity="low" if has_elevated else "info",
        evidence_ref=evidence_ref,
        attributes={
            "group_id": group_id,
            "group_email": group.get("email"),
            "group_name": group.get("name"),
            "member_count": len(members),
            "member_emails": member_emails,
            "member_roles": roles,
            "has_elevated_role": has_elevated,
        },
    )


def _event(
    *,
    org: str,
    collected_at: datetime,
    tenant_id: str,
    signal: str,
    event_type: str,
    asset_id: str,
    asset_type: str,
    controls: list[str],
    status: str,
    severity: str,
    evidence_ref: str,
    attributes: dict[str, Any],
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    stable = _stable_suffix(org=org, signal=signal, asset_id=asset_id, dedupe_key=dedupe_key)
    return {
        "event_id": f"google-workspace-{stable}",
        "tenant_id": tenant_id,
        "workspace_id": "default",
        "event_time": utc_iso(collected_at),
        "source": "google_workspace",
        "event_type": event_type,
        "entity": {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "asset_owner": org,
            "environment": "prod",
            "org": org,
        },
        "severity": severity,
        "status": status,
        "controls": controls,
        "evidence": {
            "evidence_id": f"ev-{stable}",
            "evidence_ref": evidence_ref,
            "evidence_collected_at": utc_iso(collected_at),
        },
        "attributes": attributes,
    }


def _safe_members(
    client: GoogleWorkspaceClient | GoogleWorkspaceFixtureClient,
    group_id: str,
) -> list[dict[str, Any]]:
    try:
        return client.members(group_id)
    except urllib.error.HTTPError:
        # A members read that the token cannot authorize must not abort the run;
        # the group event records an empty-membership signal instead.
        return []


def _org_slug(org_url: str) -> str:
    netloc = urllib.parse.urlparse(org_url).netloc or org_url
    return netloc.strip("/") or "google-workspace"


def _stable_suffix(*, org: str, signal: str, asset_id: str, dedupe_key: str | None) -> str:
    """Build a deterministic connector-local id without hashing identity data.

    The pipeline computes the canonical raw evidence hash after collection. These
    IDs only need to be stable for connector upserts and evidence-room links.
    """
    seed = f"{org}:{signal}:{dedupe_key or asset_id}".lower()
    return re.sub(r"[^a-z0-9_.:-]+", "-", seed).strip("-")[:96] or "google-workspace"
