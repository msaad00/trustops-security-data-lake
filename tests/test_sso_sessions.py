"""Browser session + OIDC login tests for server mode.

The OIDC redirect/token-exchange is driven by an external identity provider, so
the network flow is not unit-tested here. The provisioning + session issuance
logic (:func:`complete_oidc_login`) and the session-cookie auth path are.
"""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse.auth.oidc import OIDCConfig, OIDCLoginError, complete_oidc_login  # noqa: E402
from security_lakehouse.auth.saml import (  # noqa: E402
    SAMLConfig,
    SAMLConfigError,
    SAMLLoginError,
    complete_saml_login,
    load_saml_config,
    saml_request_data,
)
from security_lakehouse.auth.sessions import SESSION_COOKIE  # noqa: E402
from security_lakehouse.db import repository  # noqa: E402
from security_lakehouse.db.base import session_scope  # noqa: E402
from security_lakehouse.db.repository import create_tenant, create_user, create_user_session  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


def _config(*, tenant_slug: str = "acme", auto_provision: bool = False) -> OIDCConfig:
    return OIDCConfig(
        issuer="https://idp.test",
        client_id="cid",
        client_secret="sec",
        tenant_slug=tenant_slug,
        auto_provision=auto_provision,
    )


def _saml_config(*, tenant_slug: str = "acme", auto_provision: bool = False) -> SAMLConfig:
    return SAMLConfig(
        sp_entity_id="https://trustops.test/saml/metadata",
        acs_url="https://trustops.test/api/v1/auth/saml/acs",
        idp_entity_id="https://idp.test",
        idp_sso_url="https://idp.test/sso",
        idp_x509_cert="cert",
        tenant_slug=tenant_slug,
        auto_provision=auto_provision,
    )


@pytest.fixture
def app_env(tmp_path: Path):
    _seed_lake(tmp_path)
    app = create_app(tmp_path)  # auth required; OIDC not configured
    return app, TestClient(app)


def test_session_repository_lifecycle(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        user = create_user(session, tenant_id=tenant.id, email="u@acme.test", role="read_only")
        row, token = create_user_session(session, tenant_id=tenant.id, user_id=user.id)
        assert row.is_active()
    with session_scope(app.state.sessionmaker) as session:
        assert repository.resolve_user_session(session, token).is_active()
        assert repository.revoke_user_session(session, token, now=datetime.now(UTC))
    with session_scope(app.state.sessionmaker) as session:
        assert not repository.resolve_user_session(session, token).is_active()


def test_expired_session_is_inactive(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        user = create_user(session, tenant_id=tenant.id, email="u@acme.test")
        row, _token = create_user_session(session, tenant_id=tenant.id, user_id=user.id, ttl_hours=-1)
        assert not row.is_active()


def test_complete_oidc_login_requires_provisioned_user(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        create_tenant(session, slug="acme", name="Acme")
        with pytest.raises(OIDCLoginError):
            complete_oidc_login(
                session,
                config=_config(auto_provision=False),
                email="new@acme.test",
                email_verified=True,
            )


def test_complete_oidc_login_rejects_unverified_email(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        create_tenant(session, slug="acme", name="Acme")
        with pytest.raises(OIDCLoginError, match="not verified"):
            complete_oidc_login(
                session,
                config=_config(auto_provision=True),
                email="new@acme.test",
                email_verified=False,
            )


def test_complete_oidc_login_auto_provisions(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        create_tenant(session, slug="acme", name="Acme")
        user, token = complete_oidc_login(
            session,
            config=_config(auto_provision=True),
            email="new@acme.test",
            email_verified=True,
        )
        assert user.email == "new@acme.test"
        assert user.role == "read_only"
        assert repository.resolve_user_session(session, token).is_active()


def test_complete_oidc_login_unknown_tenant(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session, pytest.raises(OIDCLoginError):
        complete_oidc_login(
            session,
            config=_config(tenant_slug="ghost", auto_provision=True),
            email="x@y.test",
            email_verified=True,
        )


def test_session_cookie_authenticates(app_env) -> None:
    app, client = app_env
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        user = create_user(session, tenant_id=tenant.id, email="u@acme.test", role="read_only")
        _row, token = create_user_session(session, tenant_id=tenant.id, user_id=user.id)
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/api/v1/controls").status_code == HTTPStatus.OK
    who = client.get("/api/v1/auth/whoami").json()["data"]
    assert who["email"] == "u@acme.test"
    assert who["role"] == "read_only"


def test_logout_revokes_session(app_env) -> None:
    app, client = app_env
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        user = create_user(session, tenant_id=tenant.id, email="u@acme.test")
        _row, token = create_user_session(session, tenant_id=tenant.id, user_id=user.id)
    client.cookies.set(SESSION_COOKIE, token)
    assert client.post("/api/v1/auth/logout").status_code == HTTPStatus.OK
    client.cookies.set(SESSION_COOKIE, token)  # re-present the now-revoked token
    assert client.get("/api/v1/controls").status_code == HTTPStatus.UNAUTHORIZED


def test_login_501_when_oidc_unconfigured(app_env) -> None:
    _app, client = app_env
    assert client.get("/api/v1/auth/login").status_code == HTTPStatus.NOT_IMPLEMENTED


def test_auth_methods_reports_configured_login_surfaces(app_env) -> None:
    app, client = app_env
    app.state.oauth = object()
    app.state.oidc_config = _config()
    app.state.saml_config = _saml_config()

    resp = client.get("/api/v1/auth/methods")
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()["data"]
    assert body["require_auth"] is True
    methods = {method["id"]: method for method in body["methods"]}
    assert methods["oidc"]["configured"] is True
    assert methods["oidc"]["login_url"] == "/api/v1/auth/login"
    assert methods["oidc"]["protocol"] == "OIDC"
    assert methods["saml"]["configured"] is True
    assert methods["saml"]["login_url"] == "/api/v1/auth/saml/login"
    assert methods["saml"]["protocol"] == "SAML 2.0"
    assert methods["api_key"]["configured"] is True
    assert methods["api_key"]["login_url"] == "/api/v1/auth/keys"


def test_load_saml_config_rejects_partial_environment(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTOPS_SAML_SP_ENTITY_ID", "https://trustops.test/saml/metadata")
    with pytest.raises(SAMLConfigError):
        load_saml_config()


def test_saml_request_data_parses_post_body() -> None:
    data = saml_request_data(
        scheme="https",
        host="trustops.test",
        port=443,
        path="/api/v1/auth/saml/acs",
        query={"RelayState": "/console"},
        body=b"SAMLResponse=abc%2B123&RelayState=%2Fconsole",
    )
    assert data["https"] == "on"
    assert data["post_data"]["SAMLResponse"] == "abc+123"
    assert data["post_data"]["RelayState"] == "/console"


def test_complete_saml_login_auto_provisions(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        create_tenant(session, slug="acme", name="Acme")
        user, token = complete_saml_login(
            session,
            config=_saml_config(auto_provision=True),
            email="saml@acme.test",
        )
        assert user.email == "saml@acme.test"
        assert user.role == "read_only"
        resolved = repository.resolve_user_session(session, token)
        assert resolved.is_active()
        assert resolved.idp == "saml"


def test_complete_saml_login_requires_provisioned_user(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        create_tenant(session, slug="acme", name="Acme")
        with pytest.raises(SAMLLoginError):
            complete_saml_login(session, config=_saml_config(auto_provision=False), email="new@acme.test")


def test_saml_login_501_when_unconfigured(app_env) -> None:
    _app, client = app_env
    assert client.get("/api/v1/auth/saml/login").status_code == HTTPStatus.NOT_IMPLEMENTED
    assert client.post("/api/v1/auth/saml/acs").status_code == HTTPStatus.NOT_IMPLEMENTED


class _FakeSamlSettings:
    def get_sp_metadata(self) -> str:
        return "<EntityDescriptor />"

    def validate_metadata(self, metadata: str) -> list[str]:
        return []


class _FakeSamlAuth:
    def __init__(self, email: str = "saml@acme.test", authenticated: bool = True) -> None:
        self.email = email
        self.authenticated = authenticated

    def login(self) -> str:
        return "https://idp.test/sso?SAMLRequest=fake"

    def process_response(self) -> None:
        return None

    def get_errors(self) -> list[str]:
        return [] if self.authenticated else ["invalid_response"]

    def is_authenticated(self) -> bool:
        return self.authenticated

    def get_attributes(self) -> dict[str, list[str]]:
        return {"email": [self.email]}

    def get_nameid(self) -> str:
        return self.email

    def get_settings(self) -> _FakeSamlSettings:
        return _FakeSamlSettings()


def _set_saml_env(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTOPS_SAML_SP_ENTITY_ID", "https://trustops.test/saml/metadata")
    monkeypatch.setenv("TRUSTOPS_SAML_ACS_URL", "https://trustops.test/api/v1/auth/saml/acs")
    monkeypatch.setenv("TRUSTOPS_SAML_IDP_ENTITY_ID", "https://idp.test")
    monkeypatch.setenv("TRUSTOPS_SAML_IDP_SSO_URL", "https://idp.test/sso")
    monkeypatch.setenv("TRUSTOPS_SAML_IDP_X509_CERT", "cert")
    monkeypatch.setenv("TRUSTOPS_SAML_TENANT_SLUG", "acme")
    monkeypatch.setenv("TRUSTOPS_SAML_AUTO_PROVISION", "true")


def test_saml_endpoints_use_same_session_model(tmp_path: Path, monkeypatch) -> None:
    _set_saml_env(monkeypatch)
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    app.state.saml_auth_factory = lambda _config, _request_data: _FakeSamlAuth()
    client = TestClient(app)

    with session_scope(app.state.sessionmaker) as session:
        create_tenant(session, slug="acme", name="Acme")

    login = client.get("/api/v1/auth/saml/login", follow_redirects=False)
    assert login.status_code == HTTPStatus.FOUND
    assert login.headers["location"].startswith("https://idp.test/sso")

    metadata = client.get("/api/v1/auth/saml/metadata")
    assert metadata.status_code == HTTPStatus.OK
    assert "EntityDescriptor" in metadata.text

    acs = client.post(
        "/api/v1/auth/saml/acs",
        content=b"SAMLResponse=fake",
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert acs.status_code == HTTPStatus.FOUND
    assert SESSION_COOKIE in acs.headers["set-cookie"]

    session_token = acs.headers["set-cookie"].split(f"{SESSION_COOKIE}=", 1)[1].split(";", 1)[0]
    client.cookies.set(SESSION_COOKIE, session_token)
    who = client.get("/api/v1/auth/whoami").json()["data"]
    assert who["email"] == "saml@acme.test"
    assert who["role"] == "read_only"


def test_saml_acs_rejects_failed_response(tmp_path: Path, monkeypatch) -> None:
    _set_saml_env(monkeypatch)
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    app.state.saml_auth_factory = lambda _config, _request_data: _FakeSamlAuth(authenticated=False)
    client = TestClient(app)

    with session_scope(app.state.sessionmaker) as session:
        create_tenant(session, slug="acme", name="Acme")

    resp = client.post(
        "/api/v1/auth/saml/acs",
        content=b"SAMLResponse=fake",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
