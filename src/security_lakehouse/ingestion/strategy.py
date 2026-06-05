"""Per-source ingestion strategy: resolve a method from velocity + cost.

A compliance data layer that claims "real-time control health" must justify
*how* each signal is ingested, because streaming is not free. This module turns
declared source attributes into a recommended ingestion method using a committed
decision table — so the choice is auditable code, not prose hand-waving.

Decision table (encoded in :func:`resolve_method`):

| velocity            | native_connector | method                       | why |
|---------------------|------------------|------------------------------|-----|
| high_event_stream   | (any)            | Snowpipe Streaming           | Seconds-fresh, serverless, no warehouse COPY; ~50% cheaper than file Snowpipe at high throughput (unified ~0.0037 credits/GB). INSERT-only → upserts handled downstream via Streams/Tasks/Dynamic Tables. |
| medium_api          | true             | Managed/native connector     | Managed runtime (e.g. Snowflake Openflow), less code, vendor-managed auth, built-in observability. |
| medium_api          | false            | Committed custom pull        | No native connector exists: watermark + cursor pagination + 429 backoff + idempotent merge. |
| low_current_state   | (any)            | Scheduled pull (hourly/daily)| Slow churn; streaming would add producer cost + ops for zero freshness benefit the control needs. |

**Cost discipline:** streaming bills per client-runtime-hour + per-GB and you own
the producer. Only choose it when a control's ``freshness_slo`` actually requires
sub-minute data. The strategy enforces that — high velocity is the *only* path to
streaming, and it must be declared on the source, not assumed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from security_lakehouse.connectors import load_connector_catalog

# Declared source velocities (set per connector in connectors/catalog.json).
VELOCITIES = {"high_event_stream", "medium_api", "low_current_state"}
DATA_SHAPES = {"event_log", "current_state"}

METHOD_STREAMING = "Snowpipe Streaming"
METHOD_NATIVE = "Managed/native connector (Openflow)"
METHOD_CUSTOM_PULL = "Committed custom pull"
METHOD_SCHEDULED = "Scheduled pull"

_COST_NOTE = {
    METHOD_STREAMING: (
        "Seconds-fresh, serverless; ~0.0037 credits/GB and per client-runtime-hour. "
        "You own the producer — justified only when freshness_slo is sub-minute."
    ),
    METHOD_NATIVE: (
        "Managed runtime + vendor-managed auth; least code to own. "
        "Cost is the connector runtime, not a streaming producer."
    ),
    METHOD_CUSTOM_PULL: (
        "No native connector: watermark + cursor pagination + 429 backoff + idempotent merge. "
        "Cheap warehouse cost; engineering cost is the resilient-pull code (owned, tested)."
    ),
    METHOD_SCHEDULED: (
        "Slow-churn current state on an hourly/daily cron. "
        "Streaming would add producer cost for zero freshness benefit the control needs."
    ),
}


@dataclass(frozen=True)
class IngestionPlan:
    """The resolved ingestion decision for one source."""

    connector_id: str
    velocity: str
    method: str
    freshness_slo: str
    native_connector: bool
    data_shape: str
    cost_note: str


def freshness_slo_label(minutes: int) -> str:
    """Render ``freshness_slo_minutes`` as a compact label (e.g. ``15m``, ``1h``)."""
    if minutes < 1:
        return f"{int(minutes * 60)}s"
    if minutes < 60:
        return f"{minutes}m"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes / 60:.1f}h"


def resolve_method(velocity: str, native_connector: bool) -> str:
    """Resolve the ingestion method from velocity + native-connector availability.

    Streaming is reachable *only* from ``high_event_stream`` — the cost guard.
    """
    if velocity == "high_event_stream":
        return METHOD_STREAMING
    if velocity == "medium_api":
        return METHOD_NATIVE if native_connector else METHOD_CUSTOM_PULL
    # low_current_state and any unknown velocity default to the cheapest path.
    return METHOD_SCHEDULED


def plan_for_connector(connector_id: str, connector: dict) -> IngestionPlan:
    """Build the :class:`IngestionPlan` for one catalog entry."""
    velocity = str(connector.get("velocity") or "low_current_state")
    native = bool(connector.get("native_connector", False))
    data_shape = str(connector.get("data_shape") or "current_state")
    minutes = int(connector.get("freshness_slo_minutes") or 0)
    method = resolve_method(velocity, native)
    return IngestionPlan(
        connector_id=connector_id,
        velocity=velocity,
        method=method,
        freshness_slo=freshness_slo_label(minutes) if minutes else "unset",
        native_connector=native,
        data_shape=data_shape,
        cost_note=_COST_NOTE[method],
    )


def plan_catalog(path: str | Path | None = None) -> list[IngestionPlan]:
    """Resolve an ingestion plan for every connector in the catalog."""
    catalog = load_connector_catalog(path)
    return [plan_for_connector(cid, connector) for cid, connector in catalog.items()]
