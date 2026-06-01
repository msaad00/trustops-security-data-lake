from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from security_lakehouse.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "security_events.jsonl"
CLICKHOUSE_SCHEMA = ROOT / "deploy" / "clickhouse" / "schema.sql"
SNOWFLAKE_SCHEMA = ROOT / "deploy" / "snowflake" / "schema.sql"

GOLD_TABLES = ("control_posture", "control_tests", "asset_risk")


def _table_body(sql: str, table: str) -> str:
    """Return the column block between the opening paren of a create table."""
    pattern = re.compile(
        rf"create table if not exists\s+[\w.]*\b{table}\b\s*\((.*?)\)\s*(engine|cluster|;)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(sql)
    assert match, f"could not locate `{table}` create-table block"
    return match.group(1)


def _first_column(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip().strip(",")
        if stripped:
            return stripped.split()[0].lower()
    raise AssertionError("empty table body")


def test_clickhouse_gold_tables_lead_with_tenant_id() -> None:
    sql = CLICKHOUSE_SCHEMA.read_text(encoding="utf-8")
    for table in GOLD_TABLES:
        body = _table_body(sql, table)
        assert "tenant_id" in body.lower(), f"{table} missing tenant_id (clickhouse)"
        assert _first_column(body) == "tenant_id", f"{table} tenant_id not the first column (clickhouse)"
        order_match = re.search(
            rf"\b{table}\b.*?order by\s*\(([^)]*)\)",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        assert order_match, f"{table} missing ORDER BY (clickhouse)"
        leading_key = order_match.group(1).split(",")[0].strip().lower()
        assert leading_key == "tenant_id", f"{table} tenant_id not the leading ORDER BY key (clickhouse)"


def test_snowflake_gold_tables_lead_with_tenant_id() -> None:
    sql = SNOWFLAKE_SCHEMA.read_text(encoding="utf-8")
    upper_tables = {t: t.upper() for t in GOLD_TABLES}
    for table in GOLD_TABLES:
        body = _table_body(sql, upper_tables[table])
        assert "tenant_id" in body.lower(), f"{table} missing tenant_id (snowflake)"
        assert _first_column(body) == "tenant_id", f"{table} tenant_id not the first column (snowflake)"
        pk_match = re.search(
            rf"\b{upper_tables[table]}\b.*?primary key\s*\(([^)]*)\)",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        assert pk_match, f"{table} missing primary key (snowflake)"
        leading_pk = pk_match.group(1).split(",")[0].strip().lower()
        assert leading_pk == "tenant_id", f"{table} tenant_id not the leading PK column (snowflake)"


def _mart_tenant_ids(mart_path: str, table: str) -> set[str]:
    with sqlite3.connect(mart_path) as conn:
        rows = conn.execute(f"select distinct tenant_id from {table}").fetchall()
    return {row[0] for row in rows}


def test_run_pipeline_stamps_explicit_tenant_id(tmp_path: Path) -> None:
    result = run_pipeline(RAW, tmp_path / "lake", tenant_id="acme")
    for table in GOLD_TABLES:
        ids = _mart_tenant_ids(result.mart_path, table)
        assert ids == {"acme"}, f"{table} expected only tenant_id=acme, got {ids}"


def test_run_pipeline_defaults_tenant_id_to_default(tmp_path: Path) -> None:
    result = run_pipeline(RAW, tmp_path / "lake")
    for table in GOLD_TABLES:
        ids = _mart_tenant_ids(result.mart_path, table)
        assert ids == {"default"}, f"{table} expected only tenant_id=default, got {ids}"
