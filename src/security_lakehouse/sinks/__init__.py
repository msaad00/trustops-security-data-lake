"""Pluggable evidence sinks: land the local medallion into an external lake.

A sink reads the local ``silver``/``gold`` artifacts a pipeline run produced and
loads them into a customer-owned warehouse (Snowflake today; ClickHouse/Postgres
behind the same shape later). The local pipeline stays the source of truth; a
sink is an optional, idempotent projection of it into the customer's lake.
"""

from __future__ import annotations

from pathlib import Path

from security_lakehouse.sinks.snowflake_sink import SnowflakeSink, SnowflakeSinkConfig

__all__ = ["SnowflakeSink", "SnowflakeSinkConfig", "land_if_configured"]


def land_if_configured(lake_dir: str | Path, env: dict[str, str]) -> dict[str, int] | None:
    """Project the local medallion to Snowflake when the sink is configured.

    Returns the rows landed per table, or ``None`` when no sink is configured
    (the common case — the local lake stays the source of truth). Lazily importing
    means callers pay nothing unless ``SNOWFLAKE_*`` is set.
    """
    config = SnowflakeSinkConfig.from_env(env)
    if config is None:
        return None
    return SnowflakeSink(config).load(lake_dir)
