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
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

# Status codes that warrant a retry (rate-limit + transient gateway errors).
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


def next_delay(
    attempt: int,
    *,
    base: float = 0.5,
    cap: float = 30.0,
    retry_after: float | None = None,
    jitter: bool = True,
) -> float:
    """Seconds to sleep before retry ``attempt`` (0-indexed).

    A server ``Retry-After`` wins (capped); otherwise exponential ``base*2**n``
    with full jitter on the lower half to avoid thundering-herd retries.
    """
    if retry_after is not None:
        return max(0.0, min(float(retry_after), cap))
    delay = min(base * (2**attempt), cap)
    if jitter:
        delay = delay / 2 + random.uniform(0, delay / 2)
    return delay


def retry(
    fn: Callable[[], T],
    *,
    is_retryable: Callable[[BaseException], bool],
    retry_after: Callable[[BaseException], float | None] = lambda _exc: None,
    max_retries: int = 4,
    base: float = 0.5,
    cap: float = 30.0,
    sleep: Callable[[float], Any] = time.sleep,
) -> T:
    """Call ``fn`` with retry on classified-transient exceptions.

    ``is_retryable`` decides whether an exception is worth retrying;
    ``retry_after`` extracts a server-suggested delay (e.g. from a 429 header).
    Raises the last exception once ``max_retries`` is exhausted.
    """
    attempt = 0
    while True:
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised unless retryable
            if attempt >= max_retries or not is_retryable(exc):
                raise
            sleep(next_delay(attempt, base=base, cap=cap, retry_after=retry_after(exc)))
            attempt += 1
