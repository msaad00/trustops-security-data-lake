from __future__ import annotations

from security_lakehouse.identity import classify_identity_type


def test_console_access_classifies_human_and_service() -> None:
    assert classify_identity_type(console_access=True) == "human"
    assert classify_identity_type(console_access=False) == "service"


def test_azure_principal_type_branches() -> None:
    assert classify_identity_type(principal_type="User") == "human"
    assert classify_identity_type(principal_type="ServicePrincipal") == "service"
    assert classify_identity_type(principal_type="ManagedIdentity") == "service"
    assert classify_identity_type(principal_type="Group") == "unknown"
    # Casing/whitespace is normalized.
    assert classify_identity_type(principal_type=" user ") == "human"


def test_gcp_member_branches() -> None:
    assert classify_identity_type(member="user:admin@example.com") == "human"
    assert classify_identity_type(member="serviceAccount:reader@example.com") == "service"
    assert classify_identity_type(member="group:eng@example.com") == "unknown"
    assert classify_identity_type(member="domain:example.com") == "unknown"


def test_signal_priority_console_then_principal_then_member() -> None:
    # console_access wins over the other signals.
    assert (
        classify_identity_type(
            console_access=False,
            principal_type="User",
            member="user:a@example.com",
        )
        == "service"
    )
    # principal_type wins over member when console_access is absent.
    assert (
        classify_identity_type(
            principal_type="ServicePrincipal",
            member="user:a@example.com",
        )
        == "service"
    )


def test_default_is_unknown() -> None:
    assert classify_identity_type() == "unknown"
