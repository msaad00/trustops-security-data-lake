import pytest

from security_lakehouse.auth.presentation import (
    build_auth_methods_payload,
    detect_oidc_provider,
    detect_saml_provider,
)


@pytest.mark.parametrize(
    ("issuer", "expected_kind", "expected_label"),
    [
        (
            "https://dev-123456.okta.com/oauth2/default",
            "okta",
            "Okta",
        ),
        (
            "https://login.microsoftonline.com/tenant/v2.0",
            "azure_ad",
            "Microsoft Entra ID",
        ),
        (
            "https://login.microsoftonline.com/common/v2.0",
            "azure_ad",
            "Microsoft Entra ID",
        ),
        (
            "https://sts.windows.net/tenant-id/",
            "azure_ad",
            "Microsoft Entra ID",
        ),
        (
            "https://accounts.google.com",
            "google",
            "Google",
        ),
        (
            "https://tenant.us.auth0.com/",
            "auth0",
            "Auth0",
        ),
        (
            "https://company.onelogin.com/oidc/2",
            "onelogin",
            "OneLogin",
        ),
    ],
)
def test_detect_oidc_provider_known_hosts(
    issuer: str,
    expected_kind: str,
    expected_label: str,
) -> None:
    kind, label = detect_oidc_provider(issuer)
    assert kind == expected_kind
    assert label == expected_label


@pytest.mark.parametrize(
    "issuer",
    [
        "https://evilokta.com/oauth2/default",
        "https://okta.com.evil.example/oauth2/default",
        "https://notmicrosoftonline.com/tenant/v2.0",
        "https://login.microsoftonline.com.evil/sso",
        "https://sts.windows.net.evil/",
        "https://fakests.windows.net/",
        "https://notgoogle.com/o/oauth2",
        "https://accounts.google.com.evil/",
        "https://evilauth0.com/",
        "https://tenant.us.auth0.com.evil/",
        "https://notonelogin.com/oidc",
    ],
)
def test_detect_oidc_provider_rejects_spoof_domains(issuer: str) -> None:
    kind, label = detect_oidc_provider(issuer)
    assert kind == "generic_oidc"
    assert label == "OIDC identity provider"


@pytest.mark.parametrize(
    ("idp_sso_url", "idp_entity_id", "expected_kind", "expected_label"),
    [
        (
            "https://dev-123.okta.com/app/trustops/exkabc/sso/saml",
            "http://www.okta.com/exkabc",
            "okta_saml",
            "Okta SAML",
        ),
        (
            "https://login.microsoftonline.com/tenant/saml2",
            "https://sts.windows.net/tenant/",
            "azure_ad_saml",
            "Microsoft Entra ID SAML",
        ),
        (
            "https://login.microsoftonline.com/tenant/saml2",
            "https://identity.microsoft.com/tenant",
            "azure_ad_saml",
            "Microsoft Entra ID SAML",
        ),
        (
            "https://accounts.google.com/o/saml2/idp",
            "https://accounts.google.com/o/saml2?idpid=abc",
            "google_saml",
            "Google SAML",
        ),
        (
            "https://company.onelogin.com/trust/saml2",
            "https://app.onelogin.com/saml/metadata/123",
            "onelogin_saml",
            "OneLogin SAML",
        ),
    ],
)
def test_detect_saml_provider_known_hosts(
    idp_sso_url: str,
    idp_entity_id: str,
    expected_kind: str,
    expected_label: str,
) -> None:
    kind, label = detect_saml_provider(
        idp_sso_url=idp_sso_url,
        idp_entity_id=idp_entity_id,
    )
    assert kind == expected_kind
    assert label == expected_label


@pytest.mark.parametrize(
    ("idp_sso_url", "idp_entity_id"),
    [
        (
            "https://notokta.com/sso/saml",
            "https://login.microsoftonline.com.evil/sso",
        ),
        (
            "https://evilokta.com/sso/saml",
            "https://www.okta.com.evil.example/exkabc",
        ),
        (
            "https://notmicrosoftonline.com/saml2",
            "https://sts.windows.net.evil/",
        ),
        (
            "https://notmicrosoftonline.com/saml2",
            "https://identity.microsoft.com.evil/tenant",
        ),
        (
            "https://notgoogle.com/saml",
            "https://accounts.google.com.evil/",
        ),
        (
            "https://notonelogin.com/trust/saml2",
            "https://app.onelogin.com.evil/metadata/123",
        ),
    ],
)
def test_detect_saml_provider_rejects_spoof_domains(
    idp_sso_url: str,
    idp_entity_id: str,
) -> None:
    kind, label = detect_saml_provider(
        idp_sso_url=idp_sso_url,
        idp_entity_id=idp_entity_id,
    )
    assert kind == "generic_saml"
    assert label == "SAML identity provider"


def test_build_auth_methods_includes_api_key() -> None:
    payload = build_auth_methods_payload(
        require_auth=True,
        oidc_config=None,
        saml_config=None,
    )
    ids = {method["id"] for method in payload["methods"]}
    assert ids == {"oidc", "saml", "api_key"}
    oidc = next(m for m in payload["methods"] if m["id"] == "oidc")
    assert oidc["configured"] is False
    assert oidc["setup_hint"]


def test_build_auth_methods_oidc_metadata() -> None:
    from security_lakehouse.auth.oidc import OIDCConfig

    payload = build_auth_methods_payload(
        require_auth=True,
        oidc_config=OIDCConfig(
            issuer="https://dev-123456.okta.com/oauth2/default",
            client_id="trustops",
            client_secret="secret",
            tenant_slug="acme",
            auto_provision=True,
        ),
        saml_config=None,
    )
    oidc = next(m for m in payload["methods"] if m["id"] == "oidc")
    assert oidc["configured"] is True
    assert oidc["provider_kind"] == "okta"
    assert oidc["issuer_host"] == "dev-123456.okta.com"
    assert oidc["tenant_slug"] == "acme"
    assert oidc["auto_provision"] is True
    assert oidc["metadata_url"].endswith("/.well-known/openid-configuration")
