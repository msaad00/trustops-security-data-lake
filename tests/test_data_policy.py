"""Data sensitivity and redaction policy tests."""

from __future__ import annotations

from security_lakehouse.data_policy import redact_payload, sensitivity_allowed


def test_role_sensitivity_ceiling() -> None:
    assert sensitivity_allowed(role="security_admin", sensitivity="restricted")
    assert not sensitivity_allowed(role="security_admin", sensitivity="secret")
    assert sensitivity_allowed(role="auditor", sensitivity="internal")
    assert not sensitivity_allowed(role="auditor", sensitivity="confidential")
    assert sensitivity_allowed(role="public_share", sensitivity="public")
    assert not sensitivity_allowed(role="public_share", sensitivity="internal")


def test_auditor_redacts_owner_fields_recursively() -> None:
    payload = {
        "asset_owner": "platform",
        "nested": [{"note": "internal exception", "control_id": "SOC2-CC6.1"}],
    }

    assert redact_payload(payload, role="auditor") == {
        "asset_owner": "[redacted]",
        "nested": [{"note": "[redacted]", "control_id": "SOC2-CC6.1"}],
    }


def test_sensitivity_redacts_entire_object_when_role_is_below_ceiling() -> None:
    payload = {"sensitivity": "restricted", "finding": "secret key exposure", "asset_id": "repo:api"}

    assert redact_payload(payload, role="contributor") == {
        "sensitivity": "restricted",
        "redacted": True,
        "redaction_reason": "sensitivity exceeds role visibility",
    }
    assert redact_payload(payload, role="security_admin") == payload
