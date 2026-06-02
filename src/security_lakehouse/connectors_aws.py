"""AWS posture-evidence collector.

The third connector with a real runner. It collects read-only IAM posture
signals — IAM users and their MFA-device enrollment, plus the account password
policy — and emits them in the lake's raw evidence shape so they flow through
the same validate -> write -> pipeline path the ``github-security`` and
``okta-identity`` runners use.

Two clients sit behind one interface, mirroring ``connectors_okta``:

* :class:`AWSClient` — authenticated read-only IAM reads via ``boto3``. The
  ``boto3`` import is lazy (inside the client) so the base/test install never
  needs it; CI runs entirely off fixtures.
* :class:`AWSFixtureClient` — reads ``iam_users.json`` / ``mfa_devices.json``
  / ``password_policy.json`` from a fixture directory so collection is fully
  testable without live AWS credentials.

The collector is strictly read-only and least-privilege: it only ever issues
``ListUsers`` / ``ListMFADevices`` / ``GetAccountPasswordPolicy`` /
``GetAccountSummary`` calls and never mutates AWS state.
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
MFA_CONTROLS = ["SOC2-CC6.1", "HIPAA-164.308(a)(4)"]
POLICY_CONTROLS = ["SOC2-CC6.1", "ISO27001-A.5.15"]

# AWS-recommended password-policy floor used to score the account policy. A
# policy that meets every one of these is "strong"; anything weaker is an open
# config finding an auditor should look at.
MIN_PASSWORD_LENGTH = 14


class AWSClient:
    """Authenticated, read-only AWS IAM client backed by ``boto3``.

    ``boto3`` is imported lazily so installs that never touch live AWS do not
    need it. Credentials and region resolve through boto3's standard provider
    chain (``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` /
    ``AWS_SESSION_TOKEN`` / ``AWS_REGION`` / profiles / instance roles).
    """

    def __init__(self, *, region_name: str | None = None) -> None:
        try:
            import boto3  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - exercised only with live AWS
            raise RuntimeError("aws-posture live collection requires boto3; install it or use --fixture-dir") from exc
        self._iam = boto3.client("iam", region_name=region_name)

    def users(self) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        paginator = self._iam.get_paginator("list_users")
        for page in paginator.paginate():
            users.extend(page.get("Users", []))
        return users

    def mfa_devices(self, user_name: str) -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []
        paginator = self._iam.get_paginator("list_mfa_devices")
        for page in paginator.paginate(UserName=user_name):
            devices.extend(page.get("MFADevices", []))
        return devices

    def password_policy(self) -> dict[str, Any]:
        try:
            return self._iam.get_account_password_policy().get("PasswordPolicy", {})
        except Exception:  # noqa: BLE001 - NoSuchEntity means no policy is set
            return {}

    def account_summary(self) -> dict[str, Any]:
        try:
            return self._iam.get_account_summary().get("SummaryMap", {})
        except Exception:  # noqa: BLE001 - summary is optional context
            return {}


class AWSFixtureClient:
    """Offline AWS IAM client backed by a fixture directory."""

    def __init__(self, fixture_dir: str | Path) -> None:
        self.fixture = Path(fixture_dir)

    def users(self) -> list[dict[str, Any]]:
        return self._read_list("iam_users.json")

    def mfa_devices(self, user_name: str) -> list[dict[str, Any]]:
        payload = self._read("mfa_devices.json")
        if isinstance(payload, dict):
            items = payload.get(str(user_name), [])
            return [item for item in items if isinstance(item, dict)]
        # A flat list fixture: keep only devices that name this user.
        return [item for item in payload if isinstance(item, dict) and str(item.get("UserName")) == str(user_name)]

    def password_policy(self) -> dict[str, Any]:
        payload = self._read("password_policy.json")
        if isinstance(payload, dict):
            # Accept either a bare policy or an envelope under PasswordPolicy.
            return payload.get("PasswordPolicy", payload)
        return {}

    def account_summary(self) -> dict[str, Any]:
        payload = self._read("account_summary.json")
        if isinstance(payload, dict):
            return payload.get("SummaryMap", payload)
        return {}

    def _read(self, name: str) -> Any:
        path = self.fixture / name
        return read_json(path) if path.exists() else []

    def _read_list(self, name: str) -> list[dict[str, Any]]:
        payload = self._read(name)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []


def collect_aws_evidence(
    client: AWSClient | AWSFixtureClient,
    *,
    account_id: str,
    collected_at: datetime | None = None,
    tenant_id: str = "customer-managed",
) -> list[dict[str, Any]]:
    """Collect normalized raw posture evidence from an AWS account.

    Emits, per collection:

    * one identity-access event per IAM user (-> identity controls),
    * one MFA-enrollment event per IAM user (device count -> MFA controls,
      a user with no MFA device is a high-severity open finding),
    * one account password-policy config event (strength -> policy controls).

    Every event passes :func:`security_lakehouse.validation.validate_raw_events`.
    """
    now = collected_at or datetime.now(UTC)
    account = _account_slug(account_id)
    rows: list[dict[str, Any]] = []

    for user in client.users():
        user_name = str(user.get("UserName") or "").strip()
        if not user_name:
            continue
        rows.append(_user_event(account, user, now, tenant_id))
        devices = client.mfa_devices(user_name)
        rows.append(_mfa_event(account, user_name, user, devices, now, tenant_id))

    rows.append(_policy_event(account, client.password_policy(), now, tenant_id))
    return rows


def _user_event(
    account: str,
    user: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any]:
    user_name = str(user["UserName"])
    arn = str(user.get("Arn") or f"arn:aws:iam::{account}:user/{user_name}")
    # A user attached to an admin/privileged path is worth surfacing for review.
    path = str(user.get("Path") or "/")
    privileged = "admin" in path.lower() or "admin" in user_name.lower()
    return _event(
        account=account,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="identity_access",
        dedupe_key=user_name,
        event_type="aws.iam.user_access",
        asset_id=f"aws:iam:user/{user_name}",
        asset_type="identity_account",
        controls=IDENTITY_CONTROLS,
        # Privileged-named principals are the noteworthy ones for review.
        status="open" if privileged else "observed",
        severity="high" if privileged else "info",
        evidence_ref=arn,
        attributes={
            "user_name": user_name,
            "arn": arn,
            "user_id": user.get("UserId"),
            "path": path,
            "create_date": _iso_or_none(user.get("CreateDate")),
            "password_last_used": _iso_or_none(user.get("PasswordLastUsed")),
            "privileged": privileged,
        },
    )


def _mfa_event(
    account: str,
    user_name: str,
    user: dict[str, Any],
    devices: list[dict[str, Any]],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any]:
    device_serials = sorted(
        str(d.get("SerialNumber")) for d in devices if isinstance(d, dict) and d.get("SerialNumber")
    )
    enrolled = bool(device_serials)
    arn = str(user.get("Arn") or f"arn:aws:iam::{account}:user/{user_name}")
    # An IAM user with no MFA device is the finding worth raising.
    needs_mfa = not enrolled
    return _event(
        account=account,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="mfa_enrollment",
        dedupe_key=user_name,
        event_type="aws.iam.mfa_enrollment",
        asset_id=f"aws:iam:user/{user_name}",
        asset_type="identity_account",
        controls=MFA_CONTROLS,
        status="open" if needs_mfa else "pass",
        severity="high" if needs_mfa else "info",
        evidence_ref=f"{arn}/mfa-devices",
        attributes={
            "user_name": user_name,
            "mfa_enrolled": enrolled,
            "mfa_device_count": len(device_serials),
            "mfa_device_serials": device_serials,
            "needs_mfa": needs_mfa,
        },
    )


def _policy_event(
    account: str,
    policy: dict[str, Any],
    collected_at: datetime,
    tenant_id: str,
) -> dict[str, Any]:
    has_policy = bool(policy)
    weaknesses = _password_policy_weaknesses(policy)
    strong = has_policy and not weaknesses
    if not has_policy:
        status, severity = "open", "high"
    elif strong:
        status, severity = "pass", "info"
    else:
        status, severity = "open", "medium"
    return _event(
        account=account,
        collected_at=collected_at,
        tenant_id=tenant_id,
        signal="password_policy",
        dedupe_key="account-password-policy",
        event_type="aws.iam.password_policy",
        asset_id=f"aws:account:{account}",
        asset_type="account_config",
        controls=POLICY_CONTROLS,
        status=status,
        severity=severity,
        evidence_ref=f"arn:aws:iam::{account}:account-password-policy",
        attributes={
            "account_id": account,
            "password_policy_present": has_policy,
            "password_policy_strong": strong,
            "minimum_password_length": policy.get("MinimumPasswordLength"),
            "require_symbols": policy.get("RequireSymbols"),
            "require_numbers": policy.get("RequireNumbers"),
            "require_uppercase": policy.get("RequireUppercaseCharacters"),
            "require_lowercase": policy.get("RequireLowercaseCharacters"),
            "weaknesses": weaknesses,
        },
    )


def _password_policy_weaknesses(policy: dict[str, Any]) -> list[str]:
    if not policy:
        return ["no_password_policy"]
    weaknesses: list[str] = []
    length = policy.get("MinimumPasswordLength")
    if not isinstance(length, int) or length < MIN_PASSWORD_LENGTH:
        weaknesses.append("minimum_password_length_below_14")
    if not policy.get("RequireSymbols"):
        weaknesses.append("symbols_not_required")
    if not policy.get("RequireNumbers"):
        weaknesses.append("numbers_not_required")
    if not policy.get("RequireUppercaseCharacters"):
        weaknesses.append("uppercase_not_required")
    if not policy.get("RequireLowercaseCharacters"):
        weaknesses.append("lowercase_not_required")
    return weaknesses


def _event(
    *,
    account: str,
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
    stable = _stable_suffix(account=account, signal=signal, asset_id=asset_id, dedupe_key=dedupe_key)
    return {
        "event_id": f"aws-{stable}",
        "tenant_id": tenant_id,
        "workspace_id": "default",
        "event_time": utc_iso(collected_at),
        "source": "aws",
        "event_type": event_type,
        "entity": {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "asset_owner": account,
            "environment": "prod",
            "org": account,
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


def _iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return utc_iso(value)
    return str(value)


def _account_slug(account_id: str) -> str:
    slug = re.sub(r"[^a-z0-9_.:-]+", "-", str(account_id).lower()).strip("-")
    return slug or "aws-account"


def _stable_suffix(*, account: str, signal: str, asset_id: str, dedupe_key: str | None) -> str:
    """Build a deterministic connector-local id without hashing identity data.

    The pipeline computes the canonical raw evidence hash after collection. These
    IDs only need to be stable for connector upserts and evidence-room links.
    """
    seed = f"{account}:{signal}:{dedupe_key or asset_id}".lower()
    return re.sub(r"[^a-z0-9_.:-]+", "-", seed).strip("-")[:96] or "aws"
