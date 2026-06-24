"""Azure cloud-posture evidence collector.

The fourth connector with a real runner. It collects read-only Azure
subscription posture signals — RBAC role assignments, policy assignments, and
resource posture — and emits them in the lake's raw evidence shape so they flow
through the same validate -> write -> pipeline path the ``github-security``,
``okta-identity`` and ``aws-posture`` runners use.

Two clients sit behind one interface, mirroring ``connectors_aws``:

* :class:`AzureClient` — authenticated read-only reads via the Azure SDK
  (``azure-identity`` + ``azure-mgmt-*``). The SDK imports are lazy (inside the
  client) so the base/test install never needs them; CI runs entirely off
  fixtures.
* :class:`AzureFixtureClient` — reads ``role_assignments.json`` /
  ``policy_assignments.json`` / ``resources.json`` from a fixture directory so
  collection is fully testable without live Azure credentials.

The collector is strictly read-only and least-privilege: it only ever issues
list/read operations (``roleAssignments/read``, ``policyStates/read``,
``subscriptions/read`` and resource list reads) and never mutates Azure state.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security_lakehouse.io import read_json
from security_lakehouse.models import utc_iso

# Identity/config controls that exist in controls/catalog.json. Verified before
# wiring (SOC2-CC6.1 logical access, ISO27001-A.5.15 access control,
# HIPAA-164.308(a)(4) access management).
IDENTITY_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.5.15", "HIPAA-164.308(a)(4)"]
POLICY_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.5.15"]
RESOURCE_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.5.15"]

# Azure built-in roles that confer broad control-plane authority. A principal
# holding one of these at subscription scope is the noteworthy assignment for an
# auditor to review, so we surface it as an open finding.
PRIVILEGED_ROLE_NAMES = {"owner", "contributor", "user access administrator"}


class AzureClient:
    """Authenticated, read-only Azure subscription client backed by the SDK.

    The ``azure-identity`` / ``azure-mgmt-*`` imports are lazy so installs that
    never touch live Azure do not need them. Credentials resolve through
    ``DefaultAzureCredential`` (service-principal env vars, managed identity,
    Azure CLI login, etc.).
    """

    def __init__(self, subscription_id: str) -> None:
        try:
            from azure.identity import DefaultAzureCredential  # noqa: PLC0415
            from azure.mgmt.authorization import AuthorizationManagementClient  # noqa: PLC0415
            from azure.mgmt.resource import ResourceManagementClient  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - exercised only with live Azure
            raise RuntimeError(
                "azure-posture live collection requires azure-identity and azure-mgmt-* "
                "packages; install them or use --fixture-dir"
            ) from exc
        try:
            from azure.mgmt.resource import PolicyClient  # type: ignore[attr-defined]  # noqa: PLC0415
        except ImportError:  # pragma: no cover - depends on installed Azure SDK version
            PolicyClient = None  # type: ignore[assignment]
        self.subscription_id = subscription_id
        credential = DefaultAzureCredential()
        self._authz = AuthorizationManagementClient(credential, subscription_id)
        self._policy = PolicyClient(credential, subscription_id) if PolicyClient is not None else None
        self._resources = ResourceManagementClient(credential, subscription_id)

    def role_assignments(self) -> list[dict[str, Any]]:
        return [self._as_dict(item) for item in self._authz.role_assignments.list_for_subscription()]

    def policy_assignments(self) -> list[dict[str, Any]]:
        if self._policy is None:
            return []
        return [self._as_dict(item) for item in self._policy.policy_assignments.list()]

    def resources(self) -> list[dict[str, Any]]:
        return [self._as_dict(item) for item in self._resources.resources.list()]

    @staticmethod
    def _as_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        as_dict = getattr(item, "as_dict", None)
        if callable(as_dict):
            payload = as_dict()
            if isinstance(payload, dict):
                return payload
        return {}


class AzureFixtureClient:
    """Offline Azure client backed by a fixture directory."""

    def __init__(
        self, fixture_dir: str | Path, *, subscription_id: str = "00000000-0000-0000-0000-000000000000"
    ) -> None:
        self.fixture = Path(fixture_dir)
        self.subscription_id = subscription_id

    def role_assignments(self) -> list[dict[str, Any]]:
        return self._read_list("role_assignments.json")

    def policy_assignments(self) -> list[dict[str, Any]]:
        return self._read_list("policy_assignments.json")

    def resources(self) -> list[dict[str, Any]]:
        return self._read_list("resources.json")

    def _read(self, name: str) -> Any:
        path = self.fixture / name
        return read_json(path) if path.exists() else []

    def _read_list(self, name: str) -> list[dict[str, Any]]:
        payload = self._read(name)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []


def collect_azure_evidence(
    client: AzureClient | AzureFixtureClient,
    *,
    collected_at: datetime | None = None,
    tenant_id: str = "customer-managed",
) -> list[dict[str, Any]]:
    """Collect normalized raw posture evidence from an Azure subscription.

    Emits, per collection:

    * one role-assignment event per RBAC assignment (-> identity controls; an
      Owner / Contributor / User Access Administrator assignment at subscription
      scope is a high open finding for review),
    * one policy-assignment event per Azure Policy assignment (-> policy
      controls; a disabled enforcement mode is an open finding),
    * one resource event per subscription resource (-> resource controls).

    Every event passes :func:`security_lakehouse.validation.validate_raw_events`.
    """
    now = collected_at or datetime.now(UTC)
    subscription = _subscription_slug(client.subscription_id)
    rows: list[dict[str, Any]] = []

    for assignment in client.role_assignments():
        event = _role_assignment_event(subscription, assignment, now, tenant_id)
        if event is not None:
            rows.append(event)

    for assignment in client.policy_assignments():
        event = _policy_assignment_event(subscription, assignment, now, tenant_id)
        if event is not None:
            rows.append(event)

    for resource in client.resources():
        event = _resource_event(subscription, resource, now, tenant_id)
        if event is not None:
            rows.append(event)

    return rows


def _role_assignment_event(
    subscription: str,
    assignment: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any] | None:
    props = _props(assignment)
    assignment_id = str(assignment.get("id") or assignment.get("name") or props.get("scope") or "").strip()
    if not assignment_id:
        return None
    role_name = str(props.get("role_definition_name") or props.get("roleDefinitionName") or "").strip()
    principal_id = str(props.get("principal_id") or props.get("principalId") or "").strip()
    principal_type = str(props.get("principal_type") or props.get("principalType") or "Unknown").strip()
    scope = str(props.get("scope") or f"/subscriptions/{subscription}").strip()
    privileged = role_name.lower() in PRIVILEGED_ROLE_NAMES
    subscription_scope = scope.lower().rstrip("/").endswith(f"/subscriptions/{subscription}".lower())
    noteworthy = privileged and subscription_scope
    return _event(
        subscription=subscription,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="role_assignment",
        dedupe_key=assignment_id,
        event_type="azure.cloud.role_assignment",
        asset_id=f"azure:role-assignment:{_id_slug(assignment_id)}",
        asset_type="identity_role_assignment",
        controls=IDENTITY_CONTROLS,
        status="open" if noteworthy else "observed",
        severity="high" if noteworthy else "info",
        evidence_ref=assignment_id,
        attributes={
            "assignment_id": assignment_id,
            "role_name": role_name,
            "principal_id": principal_id,
            "principal_type": principal_type,
            "scope": scope,
            "privileged_role": privileged,
            "subscription_scope": subscription_scope,
        },
    )


def _policy_assignment_event(
    subscription: str,
    assignment: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any] | None:
    props = _props(assignment)
    assignment_id = str(assignment.get("id") or assignment.get("name") or "").strip()
    if not assignment_id:
        return None
    display_name = str(props.get("display_name") or props.get("displayName") or assignment.get("name") or "").strip()
    enforcement = str(props.get("enforcement_mode") or props.get("enforcementMode") or "Default").strip()
    scope = str(props.get("scope") or f"/subscriptions/{subscription}").strip()
    enforced = enforcement.lower() == "default"
    return _event(
        subscription=subscription,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="policy_assignment",
        dedupe_key=assignment_id,
        event_type="azure.cloud.policy_assignment",
        asset_id=f"azure:policy-assignment:{_id_slug(assignment_id)}",
        asset_type="cloud_policy",
        controls=POLICY_CONTROLS,
        # A policy assignment that is not enforcing is the noteworthy one.
        status="observed" if enforced else "open",
        severity="info" if enforced else "medium",
        evidence_ref=assignment_id,
        attributes={
            "assignment_id": assignment_id,
            "display_name": display_name,
            "enforcement_mode": enforcement,
            "is_enforced": enforced,
            "scope": scope,
            "policy_definition_id": props.get("policy_definition_id") or props.get("policyDefinitionId"),
        },
    )


def _resource_event(
    subscription: str,
    resource: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any] | None:
    resource_id = str(resource.get("id") or "").strip()
    if not resource_id:
        return None
    name = str(resource.get("name") or "").strip()
    resource_type = str(resource.get("type") or "").strip()
    location = str(resource.get("location") or "").strip()
    return _event(
        subscription=subscription,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="resource",
        dedupe_key=resource_id,
        event_type="azure.cloud.resource",
        asset_id=f"azure:resource:{_id_slug(resource_id)}",
        asset_type="cloud_resource",
        controls=RESOURCE_CONTROLS,
        status="observed",
        severity="info",
        evidence_ref=resource_id,
        attributes={
            "resource_id": resource_id,
            "resource_name": name,
            "resource_type": resource_type,
            "location": location,
            "subscription_id": subscription,
        },
    )


def _props(item: dict[str, Any]) -> dict[str, Any]:
    """Return the SDK ``properties`` sub-object, accepting flat fixtures too.

    Azure SDK ``as_dict`` payloads nest most fields under ``properties``; small
    fixtures may inline them at the top level, so we merge both views with the
    nested properties taking precedence.
    """
    merged: dict[str, Any] = {k: v for k, v in item.items() if k != "properties"}
    nested = item.get("properties")
    if isinstance(nested, dict):
        merged.update(nested)
    return merged


def _event(
    *,
    subscription: str,
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
    stable = _stable_suffix(subscription=subscription, signal=signal, asset_id=asset_id, dedupe_key=dedupe_key)
    return {
        "event_id": f"azure-{stable}",
        "tenant_id": tenant_id,
        "workspace_id": "default",
        "event_time": utc_iso(collected_at),
        "source": "azure",
        "event_type": event_type,
        "entity": {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "asset_owner": subscription,
            "environment": "prod",
            "org": subscription,
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


def _subscription_slug(subscription_id: str) -> str:
    slug = re.sub(r"[^a-z0-9_.:-]+", "-", str(subscription_id).lower()).strip("-")
    return slug or "azure-subscription"


def _id_slug(value: str) -> str:
    return _truncate_tail(re.sub(r"[^a-z0-9_.:-]+", "-", str(value).lower()).strip("-")) or "azure"


def _stable_suffix(*, subscription: str, signal: str, asset_id: str, dedupe_key: str | None) -> str:
    """Build a deterministic connector-local id without hashing identity data.

    The pipeline computes the canonical raw evidence hash after collection. These
    IDs only need to be stable for connector upserts and evidence-room links.
    Azure resource IDs share long common prefixes (the subscription and provider
    path) and carry their distinguishing name in the tail, so the slug keeps the
    tail when it exceeds the length cap.
    """
    seed = f"{subscription}:{signal}:{dedupe_key or asset_id}".lower()
    return _truncate_tail(re.sub(r"[^a-z0-9_.:-]+", "-", seed).strip("-")) or "azure"


def _truncate_tail(slug: str, *, limit: int = 96) -> str:
    """Cap a slug at ``limit`` chars, preserving the distinguishing tail."""
    if len(slug) <= limit:
        return slug
    return slug[-limit:].strip("-")
