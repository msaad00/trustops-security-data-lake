"""Outbound event webhooks: subscriptions, signing, delivery/retry, RBAC, and the
assessment-engine hook that detects new findings and newly-failing controls.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

from security_lakehouse import netguard, webhook_delivery  # noqa: E402
from security_lakehouse.assessment import verify_snapshot_chain, write_assessment_snapshot  # noqa: E402
from security_lakehouse.db import migrate  # noqa: E402
from security_lakehouse.db import webhooks as webhooks_db  # noqa: E402
from security_lakehouse.db.base import create_engine_for, session_scope  # noqa: E402
from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from security_lakehouse.services import webhooks as webhook_services  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _provision(app, slug: str, role: str = "security_admin") -> tuple[str, str]:
    """Create a tenant + user + API key; return (tenant_id, token)."""
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug=slug, name=slug.title())
        user = create_user(session, tenant_id=tenant.id, email=f"{role}@{slug}.test", role=role)
        _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
        return tenant.id, token


@pytest.fixture
def env(tmp_path: Path):
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    tokens: dict[str, str] = {}
    tenant_id = ""
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        tenant_id = tenant.id
        for role in ("read_only", "contributor", "security_admin"):
            user = create_user(session, tenant_id=tenant.id, email=f"{role}@acme.test", role=role)
            _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
            tokens[role] = token
    return app, client, tokens, tenant_id


@pytest.fixture(autouse=True)
def _public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: every host resolves to a public IP unless a test overrides it."""

    def _getaddrinfo(host, port, *args, **kwargs):  # noqa: ANN001, ARG001
        return [(2, 1, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(netguard.socket, "getaddrinfo", _getaddrinfo)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never actually sleep during retry backoff -- keeps the suite fast."""
    monkeypatch.setattr(webhook_delivery, "_backoff_sleep", lambda _s: None)


class _FakeResponse:
    """Minimal stand-in for the urlopen context-manager response."""

    def __init__(self, status: int, body: bytes = b"ok") -> None:
        self.status = status
        self._body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self, amt: int | None = None) -> bytes:
        return self._body


def _append_event(lake: Path, event: dict[str, object]) -> None:
    path = lake / "silver" / "normalized_events.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.append(event)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


_NEW_VIOLATION_EVENT_TEMPLATE = {
    "event_time": "2026-05-21T00:00:00Z",
    "event_type": "identity.access_review",
    "asset_owner": "security-platform",
    "asset_type": "iam_role",
    "environment": "prod",
    "source": "okta",
    "status": "open",
    "severity": "critical",
    "severity_score": 95,
    "raw_sha256": "xyz",
}


# --- migration ---------------------------------------------------------------


def test_migration_creates_webhook_tables(tmp_path: Path) -> None:
    migrate.upgrade(tmp_path)
    engine = create_engine_for(tmp_path)
    inspector = inspect(engine)
    assert "webhook_subscriptions" in inspector.get_table_names()
    assert "webhook_deliveries" in inspector.get_table_names()
    columns = {col["name"] for col in inspector.get_columns("webhook_subscriptions")}
    assert {"id", "tenant_id", "url", "secret", "event_types_json", "enabled"} <= columns
    index_names = {ix["name"] for ix in inspector.get_indexes("webhook_subscriptions")}
    assert "ix_webhook_subscriptions_tenant_enabled" in index_names


# --- db repository -------------------------------------------------------------


def test_subscription_crud_round_trip(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        sub = webhooks_db.create_subscription(
            session,
            tenant_id=tenant.id,
            url="https://hooks.example.com/x",
            secret="s3cr3t-value-1234",
            event_types=["assessment.completed"],
        )
        assert sub.enabled is True
        assert webhooks_db.get_subscription(session, tenant_id=tenant.id, subscription_id=sub.id) is not None
        assert len(webhooks_db.list_subscriptions(session, tenant_id=tenant.id)) == 1

        updated = webhooks_db.update_subscription(
            session, tenant_id=tenant.id, subscription_id=sub.id, changes={"enabled": False}
        )
        assert updated is not None
        assert updated.enabled is False

        assert webhooks_db.delete_subscription(session, tenant_id=tenant.id, subscription_id=sub.id) is True
        assert webhooks_db.get_subscription(session, tenant_id=tenant.id, subscription_id=sub.id) is None


def test_invalid_event_type_rejected(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        with pytest.raises(ValueError, match="unknown event type"):
            webhooks_db.create_subscription(
                session,
                tenant_id=tenant.id,
                url="https://hooks.example.com/x",
                secret="s3cr3t-value-1234",
                event_types=["not.a.real.event"],
            )


def test_secret_is_never_returned_by_default_serialization(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        sub = webhooks_db.create_subscription(
            session,
            tenant_id=tenant.id,
            url="https://hooks.example.com/x",
            secret="s3cr3t-value-1234",
            event_types=["assessment.completed"],
        )
        assert "secret" not in webhooks_db.subscription_to_dict(sub)
        assert webhooks_db.subscription_to_dict(sub, include_secret=True)["secret"] == "s3cr3t-value-1234"


# --- signing ---------------------------------------------------------------------


def test_sign_and_verify_signature_round_trip() -> None:
    """A receiver recomputes the signature over the raw body and compares."""
    body = json.dumps({"a": 1}, sort_keys=True).encode("utf-8")
    signature = webhook_delivery.sign_payload("my-secret", body)
    assert signature.startswith("sha256=")
    assert webhook_delivery.verify_signature("my-secret", body, signature) is True
    assert webhook_delivery.verify_signature("wrong-secret", body, signature) is False
    assert webhook_delivery.verify_signature("my-secret", body + b"tampered", signature) is False


# --- delivery + retry --------------------------------------------------------------


def test_deliver_webhook_success_signs_and_posts(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[urllib.request.Request] = []

    def _fake_open_guarded(request, *, timeout=None, validate=None):  # noqa: ANN001, ARG001
        captured.append(request)
        return _FakeResponse(200)

    monkeypatch.setattr(webhook_delivery.netguard, "open_guarded", _fake_open_guarded)
    envelope = webhook_delivery.build_envelope(
        event_type="assessment.completed", tenant_id="tenant-1", occurred_at="2026-01-01T00:00:00+00:00", data={"x": 1}
    )
    result = webhook_delivery.deliver_webhook(
        "https://hooks.example.com/x", secret="s3cr3t", event_type="assessment.completed", envelope=envelope
    )
    assert result == {"ok": True, "status_code": 200, "attempts": 1, "error": None}
    assert len(captured) == 1
    sent = captured[0]
    signature = sent.get_header("X-trustops-signature")
    assert signature is not None
    assert webhook_delivery.verify_signature("s3cr3t", sent.data, signature)
    assert sent.get_header("X-trustops-event") == "assessment.completed"


def test_deliver_webhook_non_2xx_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook_delivery.netguard, "open_guarded", lambda request, *, timeout=None, validate=None: _FakeResponse(500)
    )
    envelope = webhook_delivery.build_envelope(event_type="x", tenant_id="t", occurred_at="now", data={})
    result = webhook_delivery.deliver_webhook(
        "https://hooks.example.com/x", secret="s", event_type="x", envelope=envelope, max_retries=0
    )
    assert result["ok"] is False
    assert result["attempts"] == 1
    assert result["status_code"] == 500


def test_deliver_webhook_retries_and_succeeds_on_second_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def _flaky(request, *, timeout=None, validate=None):  # noqa: ANN001, ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError("boom")
        return _FakeResponse(200)

    monkeypatch.setattr(webhook_delivery.netguard, "open_guarded", _flaky)
    envelope = webhook_delivery.build_envelope(event_type="x", tenant_id="t", occurred_at="now", data={})
    result = webhook_delivery.deliver_webhook(
        "https://hooks.example.com/x", secret="s", event_type="x", envelope=envelope, max_retries=1
    )
    assert result == {"ok": True, "status_code": 200, "attempts": 2, "error": None}
    assert calls["n"] == 2


def test_deliver_webhook_exhausts_retries_and_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook_delivery.netguard,
        "open_guarded",
        lambda request, *, timeout=None, validate=None: (_ for _ in ()).throw(TimeoutError("slow receiver")),
    )
    envelope = webhook_delivery.build_envelope(event_type="x", tenant_id="t", occurred_at="now", data={})
    result = webhook_delivery.deliver_webhook(
        "https://hooks.example.com/x", secret="s", event_type="x", envelope=envelope, max_retries=1
    )
    assert result["ok"] is False
    assert result["attempts"] == 2
    assert "TimeoutError" in (result["error"] or "")


def test_deliver_webhook_ssrf_blocked_url_fails_without_an_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(netguard.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 0))])
    envelope = webhook_delivery.build_envelope(event_type="x", tenant_id="t", occurred_at="now", data={})
    result = webhook_delivery.deliver_webhook(
        "http://internal.example.com/x", secret="s", event_type="x", envelope=envelope
    )
    assert result["ok"] is False
    assert result["attempts"] == 0
    assert "SSRF" in (result["error"] or "")


# --- dispatch orchestration ---------------------------------------------------


def test_dispatch_event_fans_out_to_matching_enabled_subscriptions_only(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        match = webhooks_db.create_subscription(
            session,
            tenant_id=tenant.id,
            url="https://hooks.example.com/match",
            secret="s3cr3t-value-1234",
            event_types=["assessment.completed"],
        )
        webhooks_db.create_subscription(
            session,
            tenant_id=tenant.id,
            url="https://hooks.example.com/wrong-type",
            secret="s3cr3t-value-1234",
            event_types=["finding.created"],
        )
        webhooks_db.create_subscription(
            session,
            tenant_id=tenant.id,
            url="https://hooks.example.com/disabled",
            secret="s3cr3t-value-1234",
            event_types=["assessment.completed"],
            enabled=False,
        )
        session.commit()

        calls: list[str] = []

        def _deliver(url, *, secret, event_type, envelope):  # noqa: ANN001, ARG001
            calls.append(url)
            return {"ok": True, "status_code": 200, "attempts": 1, "error": None}

        results = webhook_services.dispatch_event(
            session, tenant.id, event_type="assessment.completed", data={"x": 1}, deliver=_deliver
        )
        assert calls == ["https://hooks.example.com/match"]
        assert len(results) == 1

        deliveries = webhook_services.list_deliveries(session, tenant.id, subscription_id=match.id)
        assert len(deliveries) == 1
        assert deliveries[0]["status"] == "success"


def test_dispatch_event_delivery_failure_is_recorded_not_raised(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        webhooks_db.create_subscription(
            session,
            tenant_id=tenant.id,
            url="https://hooks.example.com/dead",
            secret="s3cr3t-value-1234",
            event_types=["assessment.completed"],
        )
        session.commit()

        def _deliver(url, *, secret, event_type, envelope):  # noqa: ANN001, ARG001
            raise RuntimeError("network exploded")

        results = webhook_services.dispatch_event(
            session, tenant.id, event_type="assessment.completed", data={}, deliver=_deliver
        )
        assert results[0]["ok"] is False

        deliveries = webhook_services.list_deliveries(session, tenant.id)
        assert len(deliveries) == 1
        assert deliveries[0]["status"] == "failed"


# --- assessment-engine hook: violation diff + control transitions ------------------


def test_snapshot_hook_fires_only_assessment_completed_on_first_snapshot(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    calls: list[tuple] = []
    write_assessment_snapshot(tmp_path, reason="first", on_snapshot_written=lambda *a: calls.append(a))
    assert len(calls) == 1
    _path, _assessment, new_violations, newly_failing_controls = calls[0]
    # No prior snapshot to diff against -- nothing is reported as "new".
    assert new_violations == []
    assert newly_failing_controls == []


def test_snapshot_hook_detects_new_violation_and_newly_failing_control(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    write_assessment_snapshot(tmp_path, reason="baseline")  # establishes the prior snapshot, no hook

    _append_event(
        tmp_path,
        {
            **_NEW_VIOLATION_EVENT_TEMPLATE,
            "event_id": "evt-999",
            "control_ids": ["SOC2-CC7.1"],
            "asset_id": "aws:iam:role/new",
            "evidence_ref": "s3://evidence/evt-999.json",
        },
    )

    calls: list[tuple] = []
    write_assessment_snapshot(tmp_path, reason="second", on_snapshot_written=lambda *a: calls.append(a))
    assert len(calls) == 1
    _path, _assessment, new_violations, newly_failing_controls = calls[0]
    assert [v["violation_id"] for v in new_violations] == ["SOC2-CC7.1:evt-999"]
    assert newly_failing_controls == ["SOC2-CC7.1"]


def test_snapshot_hook_does_not_refire_control_failed_for_an_already_failing_control(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    write_assessment_snapshot(tmp_path, reason="baseline")  # SOC2-CC6.1 already has an open violation (evt-001)

    _append_event(
        tmp_path,
        {
            **_NEW_VIOLATION_EVENT_TEMPLATE,
            "event_id": "evt-998",
            "control_ids": ["SOC2-CC6.1"],
            "asset_id": "aws:iam:role/admin2",
            "evidence_ref": "s3://evidence/evt-998.json",
        },
    )

    calls: list[tuple] = []
    write_assessment_snapshot(tmp_path, reason="second", on_snapshot_written=lambda *a: calls.append(a))
    _path, _assessment, new_violations, newly_failing_controls = calls[0]
    assert [v["violation_id"] for v in new_violations] == ["SOC2-CC6.1:evt-998"]
    # SOC2-CC6.1 was already failing in the prior snapshot -- not a transition.
    assert newly_failing_controls == []


def test_snapshot_hook_failure_does_not_break_the_write(tmp_path: Path) -> None:
    _seed_lake(tmp_path)

    def _boom(*_args: object) -> None:
        raise RuntimeError("webhook receiver exploded")

    path = write_assessment_snapshot(tmp_path, reason="first", on_snapshot_written=_boom)
    assert path.exists()
    result = verify_snapshot_chain(tmp_path)
    assert result["ok"] is True


def test_write_assessment_snapshot_succeeds_even_when_every_webhook_delivery_fails(tmp_path: Path) -> None:
    """The real dispatch_snapshot_events hook, wired with an always-failing transport."""
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        webhooks_db.create_subscription(
            session,
            tenant_id=tenant.id,
            url="https://hooks.example.com/dead",
            secret="s3cr3t-value-1234",
            event_types=["assessment.completed"],
        )
        session.commit()

        def _always_fails(url, *, secret, event_type, envelope):  # noqa: ANN001, ARG001
            raise TimeoutError("receiver did not respond")

        def _hook(snapshot_path, assessment, new_violations, newly_failing_controls) -> None:
            webhook_services.dispatch_snapshot_events(
                session,
                tenant.id,
                snapshot_path=snapshot_path,
                assessment=assessment,
                new_violations=new_violations,
                newly_failing_controls=newly_failing_controls,
                deliver=_always_fails,
            )

        path = write_assessment_snapshot(tmp_path, reason="test", on_snapshot_written=_hook)
        assert path.exists()

        deliveries = webhook_services.list_deliveries(session, tenant.id)
        assert len(deliveries) == 1
        assert deliveries[0]["status"] == "failed"
        assert deliveries[0]["event_type"] == "assessment.completed"


# --- API ---------------------------------------------------------------------


def test_webhooks_require_auth(env) -> None:
    _app, client, _tokens, _tenant_id = env
    assert client.get("/api/v1/webhooks").status_code == HTTPStatus.UNAUTHORIZED


def test_webhook_api_crud_and_rbac(env) -> None:
    _app, client, tokens, _tenant_id = env
    # read_only can list, but creating/mutating a webhook needs connector_manage.
    assert client.get("/api/v1/webhooks", headers=_bearer(tokens["read_only"])).status_code == HTTPStatus.OK
    denied = client.post(
        "/api/v1/webhooks",
        json={"url": "https://hooks.example.com/x", "event_types": ["assessment.completed"]},
        headers=_bearer(tokens["read_only"]),
    )
    assert denied.status_code == HTTPStatus.FORBIDDEN
    # contributor (write, but not connector_manage) is denied too.
    denied_contributor = client.post(
        "/api/v1/webhooks",
        json={"url": "https://hooks.example.com/x", "event_types": ["assessment.completed"]},
        headers=_bearer(tokens["contributor"]),
    )
    assert denied_contributor.status_code == HTTPStatus.FORBIDDEN

    created = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://hooks.example.com/sink",
            "event_types": ["assessment.completed", "finding.created"],
            "description": "SIEM ingest",
        },
        headers=_bearer(tokens["security_admin"]),
    )
    assert created.status_code == HTTPStatus.CREATED
    body = created.json()["data"]
    assert body["url"] == "https://hooks.example.com/sink"
    assert body["enabled"] is True
    # The secret is handed back in full exactly once, at creation.
    assert isinstance(body.get("secret"), str) and len(body["secret"]) >= 16
    subscription_id = body["id"]

    fetched = client.get(f"/api/v1/webhooks/{subscription_id}", headers=_bearer(tokens["read_only"]))
    assert fetched.status_code == HTTPStatus.OK
    assert "secret" not in fetched.json()["data"]

    patched = client.patch(
        f"/api/v1/webhooks/{subscription_id}",
        json={"enabled": False},
        headers=_bearer(tokens["security_admin"]),
    )
    assert patched.status_code == HTTPStatus.OK
    assert patched.json()["data"]["enabled"] is False

    deleted = client.delete(f"/api/v1/webhooks/{subscription_id}", headers=_bearer(tokens["security_admin"]))
    assert deleted.status_code == HTTPStatus.OK
    assert client.get("/api/v1/webhooks", headers=_bearer(tokens["security_admin"])).json()["data"] == []


def test_webhook_invalid_event_type_is_400(env) -> None:
    _app, client, tokens, _tenant_id = env
    resp = client.post(
        "/api/v1/webhooks",
        json={"url": "https://hooks.example.com/x", "event_types": ["not.a.real.event"]},
        headers=_bearer(tokens["security_admin"]),
    )
    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_webhook_unknown_field_rejected(env) -> None:
    _app, client, tokens, _tenant_id = env
    resp = client.post(
        "/api/v1/webhooks",
        json={"url": "https://hooks.example.com/x", "event_types": ["assessment.completed"], "bogus": "field"},
        headers=_bearer(tokens["security_admin"]),
    )
    assert resp.status_code == 422


def test_webhook_tenant_isolation(tmp_path: Path) -> None:
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    _a_id, token_a = _provision(app, "acme")
    _b_id, token_b = _provision(app, "globex")

    created = client.post(
        "/api/v1/webhooks",
        json={"url": "https://hooks.example.com/a-only", "event_types": ["assessment.completed"]},
        headers=_bearer(token_a),
    )
    assert created.status_code == HTTPStatus.CREATED
    subscription_id = created.json()["data"]["id"]

    b_list = client.get("/api/v1/webhooks", headers=_bearer(token_b)).json()["data"]
    assert b_list == []
    assert client.get(f"/api/v1/webhooks/{subscription_id}", headers=_bearer(token_b)).status_code == (
        HTTPStatus.NOT_FOUND
    )
    assert (
        client.patch(
            f"/api/v1/webhooks/{subscription_id}", json={"enabled": False}, headers=_bearer(token_b)
        ).status_code
        == HTTPStatus.NOT_FOUND
    )
    assert client.delete(f"/api/v1/webhooks/{subscription_id}", headers=_bearer(token_b)).status_code == (
        HTTPStatus.NOT_FOUND
    )

    a_list = client.get("/api/v1/webhooks", headers=_bearer(token_a)).json()["data"]
    assert [w["url"] for w in a_list] == ["https://hooks.example.com/a-only"]


def test_snapshot_creation_via_api_dispatches_assessment_completed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """POST /api/v1/snapshots (the documented route) triggers a signed delivery
    after the snapshot write completes, and the outcome is auditable via the
    deliveries endpoint -- exercising the full hook wiring, not just the
    service function in isolation.
    """
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    tenant_id, admin_token = _provision(app, "acme", role="security_admin")

    calls: list[dict] = []

    def _fake_deliver(url, *, secret, event_type, envelope):  # noqa: ANN001, ARG001
        calls.append({"url": url, "secret": secret, "event_type": event_type, "envelope": envelope})
        return {"ok": True, "status_code": 200, "attempts": 1, "error": None}

    monkeypatch.setattr(webhook_services, "deliver_webhook", _fake_deliver)

    created = client.post(
        "/api/v1/webhooks",
        json={"url": "https://hooks.example.com/sink", "event_types": ["assessment.completed"]},
        headers=_bearer(admin_token),
    )
    assert created.status_code == HTTPStatus.CREATED
    subscription_id = created.json()["data"]["id"]
    secret = created.json()["data"]["secret"]

    snap = client.post("/api/v1/snapshots", json={"reason": "api_test"}, headers=_bearer(admin_token))
    assert snap.status_code == HTTPStatus.CREATED

    assert len(calls) == 1
    delivered = calls[0]
    assert delivered["event_type"] == "assessment.completed"
    assert delivered["url"] == "https://hooks.example.com/sink"
    assert delivered["secret"] == secret
    envelope = delivered["envelope"]
    assert envelope["event"] == "assessment.completed"
    assert envelope["tenant_id"] == tenant_id
    assert envelope["data"]["snapshot_reason"] == "api_test"

    deliveries = client.get(f"/api/v1/webhooks/{subscription_id}/deliveries", headers=_bearer(admin_token))
    assert deliveries.status_code == HTTPStatus.OK
    delivery_rows = deliveries.json()["data"]
    assert len(delivery_rows) == 1
    assert delivery_rows[0]["status"] == "success"
    assert delivery_rows[0]["event_type"] == "assessment.completed"


def test_snapshot_creation_via_api_does_not_fail_when_webhook_delivery_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The snapshot API call must succeed even though its subscriber is dead --
    delivery failure is recorded, never raised back through the write path."""
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app)
    _tenant_id, admin_token = _provision(app, "acme", role="security_admin")

    def _dead_receiver(url, *, secret, event_type, envelope):  # noqa: ANN001, ARG001
        raise TimeoutError("receiver did not respond")

    monkeypatch.setattr(webhook_services, "deliver_webhook", _dead_receiver)

    created = client.post(
        "/api/v1/webhooks",
        json={"url": "https://hooks.example.com/dead", "event_types": ["assessment.completed"]},
        headers=_bearer(admin_token),
    )
    assert created.status_code == HTTPStatus.CREATED
    subscription_id = created.json()["data"]["id"]

    snap = client.post("/api/v1/snapshots", json={"reason": "api_test"}, headers=_bearer(admin_token))
    assert snap.status_code == HTTPStatus.CREATED
    assert "snapshot_path" in snap.json()["data"]

    deliveries = client.get(f"/api/v1/webhooks/{subscription_id}/deliveries", headers=_bearer(admin_token))
    assert deliveries.json()["data"][0]["status"] == "failed"
