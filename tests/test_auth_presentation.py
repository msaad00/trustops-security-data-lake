from security_lakehouse.auth.presentation import (
    build_auth_methods_payload,
    detect_oidc_provider,
    detect_saml_provider,
)


def test_detect_oidc_provider_okta() -> None:
    kind, label = detect_oidc_provider("https://dev-123456.okta.com/oauth2/default")
    assert kind == "okta"
    assert label == "Okta"


def test_detect_oidc_provider_entra() -> None:
    kind, label = detect_oidc_provider("https://login.microsoftonline.com/tenant/v2.0")
    assert kind == "azure_ad"
    assert label == "Microsoft Entra ID"


def test_detect_saml_provider_okta() -> None:
    kind, label = detect_saml_provider(
        idp_sso_url="https://dev-123.okta.com/app/trustops/exkabc/sso/saml",
        idp_entity_id="http://www.okta.com/exkabc",
    )
    assert kind == "okta_saml"
    assert label == "Okta SAML"


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
