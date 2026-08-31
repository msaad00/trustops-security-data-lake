"""Exponential backoff + jitter, honoring HTTP ``Retry-After`` on 429.

API limits are a fact of ingestion at scale. :func:`retry` wraps a call and
re-tries on caller-classified transient failures, sleeping with exponential
backoff + jitter — and deferring to a server-provided ``Retry-After`` when one
is present (the correct behavior for HTTP 429). ``sleep`` is injectable so tests
never actually wait.
"""

from __future__ import annotations

import random
import time
import urllib.error
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

# Status codes that warrant a retry (rate-limit + transient gateway errors).
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


def is_retryable_http(exc: BaseException) -> bool:
    """A 429 or transient 5xx from any HTTP source is worth retrying."""
    return isinstance(exc, urllib.error.HTTPError) and exc.code in RETRYABLE_STATUS


def http_retry_after(exc: BaseException) -> float | None:
    """Read a server ``Retry-After`` (seconds) from a 429 response, if present.

    Accepts both delta-seconds (RFC 7231 integer form) and HTTP-date strings.
    """
    import email.utils

    if isinstance(exc, urllib.error.HTTPError) and exc.headers:
        raw = exc.headers.get("Retry-After")
        if not raw:
            return None
        raw = str(raw).strip()
        if raw.isdigit():
            return float(raw)
        # HTTP-date form: "Wed, 01 Jan 2026 00:00:00 GMT"
        try:
            dt = email.utils.parsedate_to_datetime(raw)
            import datetime as _dt

            delta = (dt - _dt.datetime.now(_dt.UTC)).total_seconds()
            return max(0.0, delta)
        except Exception:
            pass
    return None


def next_delay(
    attempt: int,
    *,
    base: float = 0.5,
    cap: float = 300.0,
    retry_after: float | None = None,
    jitter: bool = True,
) -> float:
    """Seconds to sleep before retry ``attempt`` (0-indexed).

    A server ``Retry-After`` wins (capped at ``cap``); otherwise exponential
    ``base*2**n`` with full jitter to avoid thundering-herd retries.
    """
    if retry_after is not None:
        return max(0.0, min(float(retry_after), cap))
    delay = min(base * (2**attempt), cap)
    if jitter:
        delay = random.uniform(0, delay)
    return delay


def retry(
    fn: Callable[[], T],
    *,
    is_retryable: Callable[[Exception], bool],
    retry_after: Callable[[Exception], float | None] = lambda _exc: None,
    max_retries: int = 4,
    base: float = 0.5,
    cap: float = 30.0,
    sleep: Callable[[float], Any] | None = None,
) -> T:
    """Call ``fn`` with retry on classified-transient exceptions.

    ``is_retryable`` decides whether an exception is worth retrying;
    ``retry_after`` extracts a server-suggested delay (e.g. from a 429 header).
    Raises the last exception once ``max_retries`` is exhausted. ``sleep``
    defaults to :func:`time.sleep`, resolved at call time so tests can patch it.
    """
    _sleep = sleep or time.sleep
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if attempt >= max_retries or not is_retryable(exc):
                raise
            _sleep(next_delay(attempt, base=base, cap=cap, retry_after=retry_after(exc)))
            attempt += 1


def http_retry(fn: Callable[[], T], **kwargs: Any) -> T:
    """Retry ``fn`` on retryable HTTP errors (429 / transient 5xx), honoring ``Retry-After``."""
    return retry(fn, is_retryable=is_retryable_http, retry_after=http_retry_after, **kwargs)
