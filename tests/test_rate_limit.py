"""API rate limiting: token-bucket unit behaviour + the 429 middleware path."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

from security_lakehouse.auth.rate_limit import RateLimitConfig, RateLimiter

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")

from fastapi.testclient import TestClient  # noqa: E402

from security_lakehouse.db.base import session_scope  # noqa: E402
from security_lakehouse.db.repository import create_api_key, create_tenant, create_user  # noqa: E402
from security_lakehouse.server_app import create_app  # noqa: E402
from test_api_v1 import _seed_lake  # noqa: E402


class _Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


# --- token bucket ------------------------------------------------------------


def test_burst_then_throttle_then_refill() -> None:
    clock = _Clock()
    limiter = RateLimiter(RateLimitConfig(rps=2.0, burst=3), clock=clock)

    # The burst capacity is allowed immediately.
    assert [limiter.check("k")[0] for _ in range(3)] == [True, True, True]
    # The 4th in the same instant is denied with a positive retry-after.
    allowed, retry_after = limiter.check("k")
    assert allowed is False
    assert retry_after > 0

    # After enough time to refill one token (rps=2 -> 0.5s/token), one passes.
    clock.advance(0.5)
    assert limiter.check("k")[0] is True
    assert limiter.check("k")[0] is False


def test_keys_are_isolated() -> None:
    clock = _Clock()
    limiter = RateLimiter(RateLimitConfig(rps=1.0, burst=1), clock=clock)
    assert limiter.check("a")[0] is True
    # A different key has its own full bucket.
    assert limiter.check("b")[0] is True
    assert limiter.check("a")[0] is False


def test_disabled_config_always_allows() -> None:
    limiter = RateLimiter(RateLimitConfig.from_env({"TRUSTOPS_API_RATE_LIMIT_RPS": "0"}))
    assert limiter.enabled is False
    assert all(limiter.check("k")[0] for _ in range(50))


def test_lru_eviction_bounds_memory() -> None:
    clock = _Clock()
    limiter = RateLimiter(RateLimitConfig(rps=1.0, burst=1, max_keys=10), clock=clock)
    for i in range(100):
        limiter.check(f"key-{i}")
    assert len(limiter._buckets) <= 10  # noqa: SLF001 - asserting the memory bound


def test_from_env_defaults_enabled() -> None:
    cfg = RateLimitConfig.from_env({})
    assert cfg.enabled is True
    assert cfg.rps > 0 and cfg.burst > 0


def test_build_rate_limiter_uses_memory_by_default() -> None:
    from security_lakehouse.auth.rate_limit_redis import build_rate_limiter

    limiter = build_rate_limiter(RateLimitConfig(rps=5.0, burst=5), {})
    assert isinstance(limiter, RateLimiter)


def test_build_rate_limiter_selects_redis_when_url_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from security_lakehouse.auth.rate_limit import ENV_REDIS_URL
    from security_lakehouse.auth.rate_limit_redis import build_rate_limiter

    created: list[str] = []

    class _StubRedisLimiter:
        def __init__(self, config, redis_url, **kwargs) -> None:
            created.append(redis_url)

        @property
        def enabled(self) -> bool:
            return True

        def check(self, key: str) -> tuple[bool, float]:
            return True, 0.0

    monkeypatch.setattr(
        "security_lakehouse.auth.rate_limit_redis.RedisRateLimiter",
        _StubRedisLimiter,
    )
    env = {ENV_REDIS_URL: "redis://redis:6379/0"}
    limiter = build_rate_limiter(RateLimitConfig(rps=5.0, burst=5), env)
    assert isinstance(limiter, _StubRedisLimiter)
    assert created == ["redis://redis:6379/0"]


# --- middleware integration --------------------------------------------------


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # A tiny limit so a couple of requests trip it deterministically.
    monkeypatch.setenv("TRUSTOPS_API_RATE_LIMIT_RPS", "1")
    monkeypatch.setenv("TRUSTOPS_API_RATE_LIMIT_BURST", "2")
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        user = create_user(session, tenant_id=tenant.id, email="dev@acme.test", role="contributor")
        _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
    return TestClient(app), token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_api_returns_429_with_retry_after_when_over_limit(client) -> None:
    test_client, token = client
    statuses = [test_client.get("/api/v1/risks", headers=_bearer(token)).status_code for _ in range(5)]
    assert statuses[0] == HTTPStatus.OK
    assert HTTPStatus.TOO_MANY_REQUESTS in statuses

    throttled = test_client.get("/api/v1/risks", headers=_bearer(token))
    assert throttled.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert int(throttled.headers["Retry-After"]) >= 1
    assert throttled.json()["errors"][0]["code"] == "rate_limited"


def test_health_probe_is_never_throttled(client) -> None:
    test_client, _token = client
    # Far more than the burst; health must always answer for orchestrators.
    assert all(test_client.get("/api/healthz").status_code == HTTPStatus.OK for _ in range(20))


def test_distinct_credentials_do_not_share_a_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUSTOPS_API_RATE_LIMIT_RPS", "1")
    monkeypatch.setenv("TRUSTOPS_API_RATE_LIMIT_BURST", "1")
    _seed_lake(tmp_path)
    app = create_app(tmp_path)
    tokens = []
    with session_scope(app.state.sessionmaker) as session:
        tenant = create_tenant(session, slug="acme", name="Acme")
        for i in range(2):
            user = create_user(session, tenant_id=tenant.id, email=f"u{i}@acme.test", role="contributor")
            _key, token = create_api_key(session, tenant_id=tenant.id, user_id=user.id)
            tokens.append(token)
    test_client = TestClient(app)
    # Each credential gets its own first request before being throttled.
    assert test_client.get("/api/v1/risks", headers=_bearer(tokens[0])).status_code == HTTPStatus.OK
    assert test_client.get("/api/v1/risks", headers=_bearer(tokens[1])).status_code == HTTPStatus.OK
