"""Pluggable evidence sinks: land the local medallion into an external lake.

A sink reads the local ``silver``/``gold`` artifacts a pipeline run produced and
loads them into a customer-owned warehouse (Snowflake today; ClickHouse/Postgres
behind the same shape later). The local pipeline stays the source of truth; a
sink is an optional, idempotent projection of it into the customer's lake.
"""

from __future__ import annotations

from pathlib import Path

from security_lakehouse.sinks.clickhouse_sink import ClickHouseSink, ClickHouseSinkConfig
from security_lakehouse.sinks.snowflake_sink import SnowflakeSink, SnowflakeSinkConfig

__all__ = [
    "ClickHouseSink",
    "ClickHouseSinkConfig",
    "SnowflakeSink",
    "SnowflakeSinkConfig",
    "land_if_configured",
]


def land_if_configured(lake_dir: str | Path, env: dict[str, str]) -> dict[str, dict[str, int]] | None:
    """Project the local medallion to every configured evidence lake.

    The lake is pluggable — Snowflake and/or ClickHouse — so a deployment can
    target either or both. Returns ``{sink_name: {table: rows}}`` for each
    configured sink, or ``None`` when none is configured (the common case — the
    local lake stays the source of truth). Lazy config means callers pay nothing
    unless ``SNOWFLAKE_*`` / ``CLICKHOUSE_*`` is set.
    """
    landed: dict[str, dict[str, int]] = {}
    snowflake = SnowflakeSinkConfig.from_env(env)
    if snowflake is not None:
        landed["snowflake"] = SnowflakeSink(snowflake).load(lake_dir)
    clickhouse = ClickHouseSinkConfig.from_env(env)
    if clickhouse is not None:
        landed["clickhouse"] = ClickHouseSink(clickhouse).load(lake_dir)
    return landed or None
