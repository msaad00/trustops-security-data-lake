"""Command line interface for TrustOps Security Data Lake."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from security_lakehouse.dashboard import render_dashboard
from security_lakehouse.io import read_jsonl
from security_lakehouse.pipeline import run_pipeline
from security_lakehouse.validation import validate_raw_events

# Risk vocabulary mirrored from security_lakehouse.db.models (RISK_LEVELS /
# RISK_STATUSES). Duplicated as plain literals so the argument parser can be
# built without importing the 'server' extra (which pulls in SQLAlchemy).
_RISK_LEVEL_CHOICES = ("low", "medium", "high", "critical")
_RISK_STATUS_CHOICES = ("open", "mitigating", "accepted", "closed")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="security-lakehouse")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate raw JSONL evidence")
    validate.add_argument("--raw", required=True, help="raw security events JSONL")
    validate.set_defaults(func=_validate)

    pipeline = sub.add_parser("pipeline", help="pipeline commands")
    pipeline_sub = pipeline.add_subparsers(dest="pipeline_command", required=True)
    run = pipeline_sub.add_parser("run", help="run bronze/silver/gold pipeline")
    run.add_argument("--raw", required=True, help="raw security events JSONL")
    run.add_argument("--out", required=True, help="security data lake output directory")
    run.add_argument("--mapping", default=None, help="optional control mapping JSON")
    run.set_defaults(func=_run_pipeline)

    connectors = sub.add_parser("connectors", help="connector catalog commands")
    connectors_sub = connectors.add_subparsers(dest="connectors_command", required=True)
    connectors_validate = connectors_sub.add_parser("validate", help="validate connector access contracts")
    connectors_validate.add_argument("--catalog", default=None, help="optional connector catalog JSON")
    connectors_validate.set_defaults(func=_connectors_validate)
    connectors_list = connectors_sub.add_parser("list", help="list connector access contracts")
    connectors_list.add_argument("--catalog", default=None, help="optional connector catalog JSON")
    connectors_list.set_defaults(func=_connectors_list)
    connectors_configure = connectors_sub.add_parser("configure", help="enable or disable a connector")
    connectors_configure.add_argument("--lake", required=True, help="security data lake output directory")
    connectors_configure.add_argument("--connector-id", required=True, help="connector id from connectors/catalog.json")
    connectors_configure.add_argument("--state", required=True, choices=["enabled", "disabled"], help="connector state")
    connectors_configure.add_argument("--actor", default="cli", help="actor recorded on the configuration event")
    connectors_configure.add_argument(
        "--sync-schedule",
        default=None,
        help="optional scheduler expression for continuous connector syncs, for example '@hourly' or 'every 15m'",
    )
    connectors_configure.add_argument(
        "--repo", default=None, help="GitHub OWNER/REPO for scheduled github-security sync"
    )
    connectors_configure.add_argument(
        "--fixture-dir",
        default=None,
        help="local fixture directory for scheduled offline connector sync",
    )
    connectors_configure.add_argument(
        "--token-env",
        default=None,
        help="environment variable containing the scheduled connector token",
    )
    connectors_configure.add_argument(
        "--no-materialize",
        action="store_true",
        help="scheduled sync collects raw evidence only; do not rebuild bronze/silver/gold outputs",
    )
    connectors_configure.set_defaults(func=_connectors_configure)
    connectors_sync = connectors_sub.add_parser("sync", help="run a configured connector into the managed raw lake")
    connectors_sync.add_argument("--lake", required=True, help="security data lake output directory")
    connectors_sync.add_argument("--connector-id", required=True, help="connector id from connectors/catalog.json")
    connectors_sync.add_argument("--repo", default=None, help="GitHub OWNER/REPO for github-security")
    connectors_sync.add_argument(
        "--fixture-dir", default=None, help="local fixture directory for offline connector sync"
    )
    connectors_sync.add_argument("--token-env", default="GITHUB_TOKEN", help="environment variable containing token")
    connectors_sync.add_argument("--actor", default="cli", help="actor recorded on the connector run")
    connectors_sync.add_argument(
        "--no-materialize",
        action="store_true",
        help="collect raw evidence only; do not rebuild bronze/silver/gold outputs",
    )
    connectors_sync.set_defaults(func=_connectors_sync)

    dashboard = sub.add_parser("dashboard", help="render static dashboard HTML")
    dashboard.add_argument("--lake", required=True, help="security data lake output directory")
    dashboard.add_argument("--out", required=True, help="dashboard HTML output path")
    dashboard.set_defaults(func=_dashboard)

    query = sub.add_parser("query", help="run read-only SQL against the analytics mart")
    query.add_argument("--lake", required=True, help="security data lake output directory")
    query.add_argument("--engine", choices=["sqlite", "duckdb"], default="sqlite", help="local mart engine")
    query.add_argument("sql", help="SQL SELECT statement")
    query.set_defaults(func=_query)

    serve = sub.add_parser("serve", help="serve the interactive console and assessment API")
    serve.add_argument("--lake", required=True, help="security data lake output directory")
    serve.add_argument("--host", default="127.0.0.1", help="bind host")
    serve.add_argument("--port", type=int, default=8787, help="bind port")
    serve.add_argument(
        "--server",
        action="store_true",
        help="run server mode on FastAPI/uvicorn (requires the 'server' extra) instead of the stdlib server",
    )
    serve.add_argument(
        "--allow-insecure-no-auth",
        action="store_true",
        help="server mode only: disable authentication (local development only)",
    )
    serve.set_defaults(func=_serve)

    assessment = sub.add_parser("assessment", help="continuous compliance assessment commands")
    assessment_sub = assessment.add_subparsers(dest="assessment_command", required=True)
    status = assessment_sub.add_parser("status", help="print current posture")
    status.add_argument("--lake", required=True, help="security data lake output directory")
    status.add_argument("--freshness-days", type=int, default=7, help="evidence freshness window")
    status.set_defaults(func=_assessment_status)
    snapshot = assessment_sub.add_parser("snapshot", help="write point-in-time assessment snapshot")
    snapshot.add_argument("--lake", required=True, help="security data lake output directory")
    snapshot.add_argument("--out", default=None, help="snapshot output path")
    snapshot.add_argument("--freshness-days", type=int, default=7, help="evidence freshness window")
    snapshot.add_argument("--reason", default="manual", help="snapshot reason")
    snapshot.set_defaults(func=_assessment_snapshot)
    violations = assessment_sub.add_parser("violations", help="list open framework/control violations")
    violations.add_argument("--lake", required=True, help="security data lake output directory")
    violations.add_argument("--framework", default=None, help="optional framework filter")
    violations.set_defaults(func=_assessment_violations)
    tests = assessment_sub.add_parser("tests", help="list continuous control tests")
    tests.add_argument("--lake", required=True, help="security data lake output directory")
    tests.add_argument(
        "--result", default=None, choices=["pass", "fail", "needs_evidence"], help="optional result filter"
    )
    tests.set_defaults(func=_assessment_tests)
    stale_evidence = assessment_sub.add_parser("stale-evidence", help="list stale, expired, or missing evidence")
    stale_evidence.add_argument("--lake", required=True, help="security data lake output directory")
    stale_evidence.add_argument(
        "--status",
        default=None,
        choices=["fresh", "stale", "expired", "missing"],
        help="optional freshness status filter",
    )
    stale_evidence.set_defaults(func=_assessment_stale_evidence)

    fixtures = sub.add_parser("fixtures", help="mockup company fixture commands")
    fixtures_sub = fixtures.add_subparsers(dest="fixtures_command", required=True)
    fixtures_list = fixtures_sub.add_parser("list", help="list available mockup company fixtures")
    fixtures_list.set_defaults(func=_fixtures_list)
    fixtures_load = fixtures_sub.add_parser("load", help="pipe a mockup company fixture through the pipeline")
    fixtures_load.add_argument("--company", required=True, help="company directory under mockup_companies/")
    fixtures_load.add_argument("--out", required=True, help="security data lake output directory")
    fixtures_load.set_defaults(func=_fixtures_load)

    repo = sub.add_parser("repo", help="public repository audit commands")
    repo_sub = repo.add_subparsers(dest="repo_command", required=True)
    repo_audit = repo_sub.add_parser("audit", help="audit a public GitHub repository without credentials")
    repo_audit.add_argument("repo", help="public GitHub URL or OWNER/REPO")
    repo_audit.add_argument("--out", required=True, help="raw evidence JSONL output path")
    repo_audit.add_argument("--fixture-dir", default=None, help="local fixture directory for offline tests and demos")
    repo_audit.set_defaults(func=_repo_audit)
    repo_governance = repo_sub.add_parser(
        "governance-sync", help="sync authenticated GitHub repository governance evidence"
    )
    repo_governance.add_argument("repo", help="GitHub URL or OWNER/REPO")
    repo_governance.add_argument("--out", required=True, help="raw evidence JSONL output path")
    repo_governance.add_argument("--fixture-dir", default=None, help="local fixture directory for offline tests")
    repo_governance.add_argument("--token-env", default="GITHUB_TOKEN", help="environment variable containing token")
    repo_governance.set_defaults(func=_repo_governance_sync)

    frameworks = sub.add_parser("frameworks", help="framework registry commands")
    frameworks_sub = frameworks.add_subparsers(dest="frameworks_command", required=True)
    frameworks_sync = frameworks_sub.add_parser(
        "sync", help="re-fetch official sources, recompute sha256, advance pulled_at"
    )
    frameworks_sync.add_argument(
        "--allow-network",
        action="store_true",
        help="fetch official sources (default is offline = mark every framework skipped)",
    )
    frameworks_sync.set_defaults(func=_frameworks_sync)
    frameworks_readiness = frameworks_sub.add_parser("readiness", help="show staged readiness gates per framework")
    frameworks_readiness.set_defaults(func=_frameworks_readiness)
    frameworks_coverage = frameworks_sub.add_parser("coverage", help="show the source-linked framework coverage ledger")
    frameworks_coverage.add_argument("--format", choices=["json", "markdown"], default="json", help="output format")
    frameworks_coverage.set_defaults(func=_frameworks_coverage)

    scheduler = sub.add_parser("scheduler", help="trigger.cron workflow scheduler")
    scheduler_sub = scheduler.add_subparsers(dest="scheduler_command", required=True)
    scheduler_tick_cmd = scheduler_sub.add_parser("tick", help="fire every due cron workflow once")
    scheduler_tick_cmd.add_argument("--lake", required=True, help="security data lake output directory")
    scheduler_tick_cmd.set_defaults(func=_scheduler_tick)
    scheduler_run_cmd = scheduler_sub.add_parser("run", help="run the scheduler daemon")
    scheduler_run_cmd.add_argument("--lake", required=True, help="security data lake output directory")
    scheduler_run_cmd.add_argument("--tick-seconds", type=int, default=60, help="seconds between ticks (default 60)")
    scheduler_run_cmd.set_defaults(func=_scheduler_run)

    db = sub.add_parser("db", help="server-mode application-state database (requires the 'server' extra)")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_upgrade = db_sub.add_parser("upgrade", help="create/upgrade the application-state schema")
    db_upgrade.add_argument("--lake", required=True, help="security data lake output directory")
    db_upgrade.add_argument("--revision", default="head", help="target Alembic revision (default head)")
    db_upgrade.set_defaults(func=_db_upgrade)
    db_current = db_sub.add_parser("current", help="print the current application-state schema revision")
    db_current.add_argument("--lake", required=True, help="security data lake output directory")
    db_current.set_defaults(func=_db_current)

    auth = sub.add_parser("auth", help="server-mode auth: tenants, users, API keys (requires the 'server' extra)")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    auth_tenant = auth_sub.add_parser("create-tenant", help="create a tenant/workspace")
    auth_tenant.add_argument("--lake", required=True, help="security data lake output directory")
    auth_tenant.add_argument("--slug", required=True, help="unique tenant slug")
    auth_tenant.add_argument("--name", required=True, help="tenant display name")
    auth_tenant.set_defaults(func=_auth_create_tenant)
    auth_user = auth_sub.add_parser("create-user", help="create a user in a tenant")
    auth_user.add_argument("--lake", required=True, help="security data lake output directory")
    auth_user.add_argument("--tenant-slug", required=True, help="tenant slug")
    auth_user.add_argument("--email", required=True, help="user email (unique within the tenant)")
    auth_user.add_argument("--display-name", default="", help="user display name")
    auth_user.add_argument(
        "--role",
        default="read_only",
        choices=["admin", "security_admin", "contributor", "auditor", "read_only"],
        help="role: admin/security_admin/contributor/auditor/read_only",
    )
    auth_user.set_defaults(func=_auth_create_user)
    auth_key = auth_sub.add_parser("issue-key", help="mint an API key for a user (printed once)")
    auth_key.add_argument("--lake", required=True, help="security data lake output directory")
    auth_key.add_argument("--tenant-slug", required=True, help="tenant slug")
    auth_key.add_argument("--email", required=True, help="user email the key acts as")
    auth_key.add_argument("--name", default="", help="key label")
    auth_key.add_argument("--expires-days", type=int, default=None, help="optional expiry in days")
    auth_key.set_defaults(func=_auth_issue_key)
    auth_revoke = auth_sub.add_parser("revoke-key", help="revoke an API key by id")
    auth_revoke.add_argument("--lake", required=True, help="security data lake output directory")
    auth_revoke.add_argument("--tenant-slug", required=True, help="tenant slug")
    auth_revoke.add_argument("--key-id", required=True, help="API key id")
    auth_revoke.set_defaults(func=_auth_revoke_key)
    auth_list = auth_sub.add_parser("list-keys", help="list API keys for a tenant")
    auth_list.add_argument("--lake", required=True, help="security data lake output directory")
    auth_list.add_argument("--tenant-slug", required=True, help="tenant slug")
    auth_list.set_defaults(func=_auth_list_keys)

    platform = sub.add_parser("platform", help="server-mode platform bootstrap commands")
    platform_sub = platform.add_subparsers(dest="platform_command", required=True)
    seed_dev = platform_sub.add_parser("seed-dev", help="seed a local dev tenant, admin user, and API key")
    seed_dev.add_argument("--lake", required=True, help="security data lake output directory")
    seed_dev.add_argument("--tenant-slug", default="dev", help="tenant slug")
    seed_dev.add_argument("--tenant-name", default="Development", help="tenant display name")
    seed_dev.add_argument("--email", default="admin@localhost", help="admin user email")
    seed_dev.add_argument("--display-name", default="Local Admin", help="admin user display name")
    seed_dev.set_defaults(func=_platform_seed_dev)

    risk = sub.add_parser("risk", help="server-mode GRC risk register (requires the 'server' extra)")
    risk_sub = risk.add_subparsers(dest="risk_command", required=True)
    risk_list = risk_sub.add_parser("list", help="list risks in a tenant register")
    risk_list.add_argument("--lake", required=True, help="security data lake output directory")
    risk_list.add_argument("--tenant", required=True, help="tenant slug")
    risk_list.add_argument("--status", default=None, choices=list(_RISK_STATUS_CHOICES), help="optional status filter")
    risk_list.add_argument(
        "--severity", default=None, choices=list(_RISK_LEVEL_CHOICES), help="optional severity filter"
    )
    risk_list.add_argument("--owner", default=None, help="optional owner filter")
    risk_list.set_defaults(func=_risk_list)
    risk_add = risk_sub.add_parser("add", help="add a risk to a tenant register")
    risk_add.add_argument("--lake", required=True, help="security data lake output directory")
    risk_add.add_argument("--tenant", required=True, help="tenant slug")
    risk_add.add_argument("--title", required=True, help="risk title")
    risk_add.add_argument("--description", default="", help="risk description")
    risk_add.add_argument("--category", default="", help="risk category")
    risk_add.add_argument("--severity", default="medium", choices=list(_RISK_LEVEL_CHOICES), help="risk severity")
    risk_add.add_argument("--likelihood", default="medium", choices=list(_RISK_LEVEL_CHOICES), help="risk likelihood")
    risk_add.add_argument("--impact", default="medium", choices=list(_RISK_LEVEL_CHOICES), help="risk impact")
    risk_add.add_argument("--owner", default="", help="risk owner")
    risk_add.add_argument("--control-id", default=None, help="linked control id")
    risk_add.set_defaults(func=_risk_add)

    workflow = sub.add_parser("workflow", help="lake-backed automation workflow engine")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_list = workflow_sub.add_parser("list", help="list saved workflows (latest version per workflow)")
    workflow_list.add_argument("--lake", required=True, help="security data lake output directory")
    workflow_list.set_defaults(func=_workflow_list)
    workflow_run = workflow_sub.add_parser("run", help="execute a saved workflow and print the run record")
    workflow_run.add_argument("--lake", required=True, help="security data lake output directory")
    workflow_run.add_argument("--id", required=True, dest="workflow_id", help="workflow_id to run")
    workflow_run.add_argument("--actor", default="api", choices=["api", "console", "scheduler"], help="run actor")
    workflow_run.set_defaults(func=_workflow_run)

    policy = sub.add_parser("policy", help="controls-as-code policy engine")
    policy_sub = policy.add_subparsers(dest="policy_command", required=True)
    policy_lint = policy_sub.add_parser("lint", help="validate every control's evaluation_rule in the catalog")
    policy_lint.add_argument("--catalog", default=None, help="optional controls catalog JSON")
    policy_lint.set_defaults(func=_policy_lint)
    policy_rules = policy_sub.add_parser("rules", help="list the built-in named rules")
    policy_rules.set_defaults(func=_policy_rules)

    openapi = sub.add_parser("openapi", help="export the server-mode OpenAPI schema (requires the 'server' extra)")
    openapi.add_argument("--out", default=None, help="write JSON to this path (default stdout)")
    openapi.set_defaults(func=_openapi)

    return parser


def _validate(args: argparse.Namespace) -> int:
    rows = read_jsonl(args.raw)
    errors = validate_raw_events(rows)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"valid raw evidence: {len(rows)} records")
    return 0


def _run_pipeline(args: argparse.Namespace) -> int:
    result = run_pipeline(args.raw, args.out, mapping_path=args.mapping)
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


def _connectors_validate(args: argparse.Namespace) -> int:
    from security_lakehouse.connectors import validate_connector_catalog

    errors = validate_connector_catalog(args.catalog)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("valid connector catalog")
    return 0


def _connectors_list(args: argparse.Namespace) -> int:
    from security_lakehouse.connectors import load_connector_catalog

    connectors = load_connector_catalog(args.catalog)
    rows = [
        {
            "connector_id": connector["connector_id"],
            "name": connector["name"],
            "collection_mode": connector["collection_mode"],
            "access_boundary": connector["access_boundary"],
            "default_route": connector["default_route"],
            "freshness_slo_minutes": connector["freshness_slo_minutes"],
        }
        for connector in connectors.values()
    ]
    print(json.dumps({"connectors": rows, "count": len(rows)}, indent=2, sort_keys=True))
    return 0


def _connectors_configure(args: argparse.Namespace) -> int:
    from security_lakehouse.connector_state import append_config_event

    options = {
        key: value
        for key, value in {
            "sync_schedule": args.sync_schedule,
            "repo": args.repo,
            "fixture_dir": args.fixture_dir,
            "token_env": args.token_env,
            "materialize": False if args.no_materialize else None,
        }.items()
        if value is not None
    }
    event = append_config_event(
        args.lake,
        connector_id=args.connector_id,
        state=args.state,
        actor=args.actor,
        options=options,
    )
    print(json.dumps({"event": event}, indent=2, sort_keys=True))
    return 0


def _connectors_sync(args: argparse.Namespace) -> int:
    from security_lakehouse.connector_runner import run_connector_sync

    result = run_connector_sync(
        args.lake,
        connector_id=args.connector_id,
        actor=args.actor,
        repo=args.repo,
        fixture_dir=args.fixture_dir,
        token_env=args.token_env,
        materialize=not args.no_materialize,
    )
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


def _dashboard(args: argparse.Namespace) -> int:
    output = render_dashboard(args.lake, args.out)
    print(f"wrote dashboard: {output}")
    return 0


def _query(args: argparse.Namespace) -> int:
    sql = args.sql.strip()
    if not sql.lower().startswith("select"):
        raise ValueError("query command only allows SELECT statements")
    if args.engine == "duckdb":
        rows = _query_duckdb(Path(args.lake) / "mart" / "security_data_lake.duckdb", sql)
        print(
            json.dumps({"count": len(rows), "engine": args.engine, "rows": rows}, indent=2, sort_keys=True, default=str)
        )
        return 0

    mart = Path(args.lake) / "mart" / "security_lakehouse.sqlite"
    with sqlite3.connect(mart) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(sql).fetchall()]
    print(json.dumps({"count": len(rows), "engine": args.engine, "rows": rows}, indent=2, sort_keys=True))
    return 0


def _query_duckdb(mart: Path, sql: str) -> list[dict]:
    if not mart.exists():
        raise ValueError("DuckDB mart not found. Install with `pip install -e '.[analytics]'` and rerun the pipeline.")
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError("DuckDB is not installed. Install with `pip install -e '.[analytics]'`.") from exc

    with duckdb.connect(str(mart), read_only=True) as conn:
        cursor = conn.execute(sql)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _serve(args: argparse.Namespace) -> int:
    if getattr(args, "server", False):
        try:
            from security_lakehouse.server_app import serve
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "server mode requires the 'server' extra: pip install 'trustops-security-data-lake[server]'"
            ) from exc
        require_auth = not getattr(args, "allow_insecure_no_auth", False)
        mode = "server mode" if require_auth else "server mode, INSECURE no-auth"
        print(f"serving TrustOps console ({mode}): http://{args.host}:{args.port}/")
        serve(args.lake, host=args.host, port=args.port, require_auth=require_auth)
    else:
        from security_lakehouse.server import serve

        print(f"serving TrustOps console: http://{args.host}:{args.port}/")
        serve(args.lake, host=args.host, port=args.port)
    return 0


def _db_upgrade(args: argparse.Namespace) -> int:
    try:
        from security_lakehouse.db import migrate
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "the db commands require the 'server' extra: pip install 'trustops-security-data-lake[server]'"
        ) from exc
    url = migrate.upgrade(args.lake, revision=args.revision)
    print(f"application-state database upgraded to {args.revision}: {url}")
    return 0


def _db_current(args: argparse.Namespace) -> int:
    try:
        from security_lakehouse.db import migrate
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "the db commands require the 'server' extra: pip install 'trustops-security-data-lake[server]'"
        ) from exc
    print(migrate.current(args.lake) or "(no revision applied)")
    return 0


def _auth_session(lake: str):
    """Ensure the schema exists and return a transactional session scope."""
    try:
        from security_lakehouse.db import migrate
        from security_lakehouse.db.base import create_engine_for, session_factory, session_scope
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "the auth commands require the 'server' extra: pip install 'trustops-security-data-lake[server]'"
        ) from exc
    migrate.upgrade(lake)
    return session_scope(session_factory(create_engine_for(lake)))


def _auth_resolve_tenant(session, slug: str):
    from security_lakehouse.db import repository

    tenant = repository.get_tenant_by_slug(session, slug=slug)
    if tenant is None:
        raise SystemExit(f"no tenant with slug {slug!r}; create it with `auth create-tenant`")
    return tenant


def _auth_create_tenant(args: argparse.Namespace) -> int:
    from security_lakehouse.db import repository

    with _auth_session(args.lake) as session:
        tenant = repository.create_tenant(session, slug=args.slug, name=args.name)
        print(f"created tenant {tenant.slug} ({tenant.id})")
    return 0


def _auth_create_user(args: argparse.Namespace) -> int:
    from security_lakehouse.db import repository

    with _auth_session(args.lake) as session:
        tenant = _auth_resolve_tenant(session, args.tenant_slug)
        user = repository.create_user(
            session, tenant_id=tenant.id, email=args.email, display_name=args.display_name, role=args.role
        )
        print(f"created user {user.email} (role={user.role}, id={user.id})")
    return 0


def _auth_issue_key(args: argparse.Namespace) -> int:
    from security_lakehouse.db import repository

    with _auth_session(args.lake) as session:
        tenant = _auth_resolve_tenant(session, args.tenant_slug)
        user = repository.get_user_by_email(session, tenant_id=tenant.id, email=args.email)
        if user is None:
            raise SystemExit(f"no user {args.email!r} in tenant {tenant.slug!r}; create it with `auth create-user`")
        expires_at = None
        if args.expires_days is not None:
            from datetime import UTC, datetime, timedelta

            expires_at = datetime.now(UTC) + timedelta(days=args.expires_days)
        key, _token = repository.create_api_key(
            session, tenant_id=tenant.id, user_id=user.id, name=args.name, expires_at=expires_at
        )
        print(
            json.dumps(
                {
                    "tenant": tenant.slug,
                    "user_email": user.email,
                    "api_key_id": key.id,
                    "prefix": key.prefix,
                    "status": key.status,
                    "secret_returned": False,
                    "note": "CLI output is non-secret; use the authenticated API creation endpoint for one-time raw key return.",
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _auth_list_keys(args: argparse.Namespace) -> int:
    from security_lakehouse.db import repository

    with _auth_session(args.lake) as session:
        tenant = _auth_resolve_tenant(session, args.tenant_slug)
        rows = [
            {
                "id": key.id,
                "name": key.name,
                "prefix": key.prefix,
                "user_id": key.user_id,
                "user_email": key.user.email,
                "role": key.role,
                "status": key.status,
                "workspace_id": key.workspace_id,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
            }
            for key in repository.list_api_keys(session, tenant_id=tenant.id)
        ]
    print(json.dumps({"tenant": args.tenant_slug, "count": len(rows), "api_keys": rows}, indent=2, sort_keys=True))
    return 0


def _auth_revoke_key(args: argparse.Namespace) -> int:
    from datetime import UTC, datetime

    from security_lakehouse.db import repository

    with _auth_session(args.lake) as session:
        tenant = _auth_resolve_tenant(session, args.tenant_slug)
        revoked = repository.revoke_api_key(session, tenant_id=tenant.id, key_id=args.key_id, now=datetime.now(UTC))
    print("revoked" if revoked else "not found or already revoked")
    return 0


def _platform_seed_dev(args: argparse.Namespace) -> int:
    from security_lakehouse.db import repository

    with _auth_session(args.lake) as session:
        tenant = repository.get_tenant_by_slug(session, slug=args.tenant_slug)
        if tenant is None:
            tenant = repository.create_tenant(session, slug=args.tenant_slug, name=args.tenant_name)
        user = repository.get_user_by_email(session, tenant_id=tenant.id, email=args.email)
        if user is None:
            user = repository.create_user(
                session,
                tenant_id=tenant.id,
                email=args.email,
                display_name=args.display_name,
                role="admin",
            )
        key, _token = repository.create_api_key(session, tenant_id=tenant.id, user_id=user.id, name="local-dev")
        result = {
            "tenant_id": tenant.id,
            "tenant_slug": tenant.slug,
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "api_key_id": key.id,
            "api_key_prefix": key.prefix,
            "secret_returned": False,
            "note": "Seeded dev principal and key metadata. CLI output is non-secret.",
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _risk_list(args: argparse.Namespace) -> int:
    from security_lakehouse.db import risks

    with _auth_session(args.lake) as session:
        tenant = _auth_resolve_tenant(session, args.tenant)
        rows = [
            risks.risk_to_dict(risk)
            for risk in risks.list_risks(
                session,
                tenant_id=tenant.id,
                status=args.status,
                severity=args.severity,
                owner=args.owner,
            )
        ]
    print(json.dumps({"tenant": tenant.slug, "count": len(rows), "risks": rows}, indent=2, sort_keys=True))
    return 0


def _risk_add(args: argparse.Namespace) -> int:
    from security_lakehouse.db import risks

    with _auth_session(args.lake) as session:
        tenant = _auth_resolve_tenant(session, args.tenant)
        risk = risks.create_risk(
            session,
            tenant_id=tenant.id,
            title=args.title,
            description=args.description,
            category=args.category,
            severity=args.severity,
            likelihood=args.likelihood,
            impact=args.impact,
            owner=args.owner,
            control_id=args.control_id,
        )
        payload = risks.risk_to_dict(risk)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _workflow_list(args: argparse.Namespace) -> int:
    from security_lakehouse.workflows import list_workflows

    rows = list_workflows(args.lake)
    print(json.dumps({"count": len(rows), "workflows": rows}, indent=2, sort_keys=True))
    return 0


def _workflow_run(args: argparse.Namespace) -> int:
    from security_lakehouse.workflows import run_workflow

    run = run_workflow(args.lake, workflow_id=args.workflow_id, actor=args.actor)
    print(json.dumps(run, indent=2, sort_keys=True))
    return 0


def _assessment_status(args: argparse.Namespace) -> int:
    from security_lakehouse.assessment import build_current_posture

    posture = build_current_posture(args.lake, freshness_days=args.freshness_days)
    print(json.dumps(posture, indent=2, sort_keys=True))
    return 0


def _assessment_snapshot(args: argparse.Namespace) -> int:
    from security_lakehouse.assessment import write_assessment_snapshot

    path = write_assessment_snapshot(args.lake, output=args.out, freshness_days=args.freshness_days, reason=args.reason)
    print(f"wrote assessment snapshot: {path}")
    return 0


def _assessment_violations(args: argparse.Namespace) -> int:
    from security_lakehouse.assessment import build_current_posture

    posture = build_current_posture(args.lake)
    framework_controls = {
        control["control_id"]: control["framework"]
        for control in read_jsonl(Path(args.lake) / "gold" / "control_posture.jsonl")
    }
    rows = [
        violation
        for violation in posture["violations"]
        if args.framework is None or framework_controls.get(violation["control_id"]) == args.framework
    ]
    print(json.dumps({"count": len(rows), "violations": rows}, indent=2, sort_keys=True))
    return 0


def _fixtures_list(_args: argparse.Namespace) -> int:
    from security_lakehouse.fixtures import list_fixtures

    rows = [
        {
            "company": fixture.company,
            "raw_path": str(fixture.raw_path),
            "event_count": fixture.event_count,
            "sources": fixture.sources,
            "controls": fixture.controls,
        }
        for fixture in list_fixtures()
    ]
    print(json.dumps({"count": len(rows), "fixtures": rows}, indent=2, sort_keys=True))
    return 0


def _fixtures_load(args: argparse.Namespace) -> int:
    from security_lakehouse.fixtures import find_fixture

    fixture = find_fixture(args.company)
    if fixture is None:
        raise ValueError(f"unknown fixture {args.company!r}; run `security-lakehouse fixtures list` to see the options")
    result = run_pipeline(fixture.raw_path, args.out)
    print(
        json.dumps(
            {
                "company": fixture.company,
                "loaded_from": str(fixture.raw_path),
                **result.__dict__,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _repo_audit(args: argparse.Namespace) -> int:
    from security_lakehouse.repo_audit import audit_public_repo

    rows = audit_public_repo(args.repo, out=args.out, fixture_dir=args.fixture_dir)
    signals = sorted({row["event_type"] for row in rows})
    print(json.dumps({"count": len(rows), "out": args.out, "signals": signals}, indent=2, sort_keys=True))
    return 0


def _repo_governance_sync(args: argparse.Namespace) -> int:
    from security_lakehouse.repo_governance import sync_repo_governance

    rows = sync_repo_governance(args.repo, out=args.out, fixture_dir=args.fixture_dir, token_env=args.token_env)
    signals = sorted({row["event_type"] for row in rows})
    print(json.dumps({"count": len(rows), "out": args.out, "signals": signals}, indent=2, sort_keys=True))
    return 0


def _frameworks_sync(args: argparse.Namespace) -> int:
    from security_lakehouse.framework_sync import sync_frameworks

    results = sync_frameworks(allow_network=args.allow_network)
    rows = [
        {
            "framework_id": r.framework_id,
            "state": r.state,
            "old_sha": r.old_sha,
            "new_sha": r.new_sha,
            "pulled_at": r.pulled_at,
            "reason": r.reason,
        }
        for r in results
    ]
    print(json.dumps({"count": len(rows), "results": rows}, indent=2, sort_keys=True))
    return 0


def _frameworks_readiness(_args: argparse.Namespace) -> int:
    from security_lakehouse.readiness import build_readiness_view

    rows = build_readiness_view()
    print(json.dumps({"count": len(rows), "frameworks": rows}, indent=2, sort_keys=True))
    return 0


def _frameworks_coverage(args: argparse.Namespace) -> int:
    from security_lakehouse.framework_coverage import (
        build_framework_coverage,
        framework_coverage_summary,
        render_framework_coverage_markdown,
    )

    rows = build_framework_coverage()
    if args.format == "markdown":
        print(render_framework_coverage_markdown(rows))
    else:
        print(
            json.dumps(
                {"summary": framework_coverage_summary(rows), "frameworks": rows},
                indent=2,
                sort_keys=True,
            )
        )
    return 0


def _scheduler_tick(args: argparse.Namespace) -> int:
    from security_lakehouse.scheduler import tick

    results = tick(args.lake)
    print(json.dumps({"fired": len(results), "results": results}, indent=2, sort_keys=True))
    return 0


def _scheduler_run(args: argparse.Namespace) -> int:
    from security_lakehouse.scheduler import run_forever

    print(f"scheduler running every {args.tick_seconds}s against {args.lake}; Ctrl-C to stop")
    run_forever(args.lake, tick_seconds=args.tick_seconds)
    return 0


def _assessment_tests(args: argparse.Namespace) -> int:
    rows = read_jsonl(Path(args.lake) / "gold" / "control_tests.jsonl")
    if args.result:
        rows = [row for row in rows if row["result"] == args.result]
    print(json.dumps({"count": len(rows), "control_tests": rows}, indent=2, sort_keys=True))
    return 0


def _assessment_stale_evidence(args: argparse.Namespace) -> int:
    path = Path(args.lake) / "gold" / "evidence_freshness.jsonl"
    if path.exists():
        rows = read_jsonl(path)
    else:
        from security_lakehouse.evidence_freshness import build_evidence_freshness

        rows = build_evidence_freshness(read_jsonl(Path(args.lake) / "silver" / "normalized_events.jsonl"))
    if args.status:
        rows = [row for row in rows if row["status"] == args.status]
    else:
        rows = [row for row in rows if row["status"] in {"stale", "expired", "missing"}]
    print(json.dumps({"count": len(rows), "evidence": rows}, indent=2, sort_keys=True))
    return 0


def _policy_lint(args: argparse.Namespace) -> int:
    from security_lakehouse.controls import DEFAULT_CATALOG_PATH
    from security_lakehouse.io import read_json
    from security_lakehouse.policy import validate_rule

    catalog = read_json(args.catalog or DEFAULT_CATALOG_PATH)
    controls = catalog.get("controls", []) if isinstance(catalog, dict) else []
    failures: list[str] = []
    for control in controls:
        control_id = str(control.get("control_id", "?"))
        for problem in validate_rule(control.get("evaluation_rule")):
            failures.append(f"{control_id}: {problem}")
    if failures:
        print("policy lint failed:\n" + "\n".join(f"  - {f}" for f in failures))
        return 1
    print(f"policy lint passed: {len(controls)} control rule(s) valid")
    return 0


def _policy_rules(args: argparse.Namespace) -> int:
    from security_lakehouse.policy import NAMED_RULES

    print(json.dumps(NAMED_RULES, indent=2, sort_keys=True))
    return 0


def _openapi(args: argparse.Namespace) -> int:
    import tempfile

    try:
        from security_lakehouse.server_app import create_app
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "the openapi command requires the 'server' extra: pip install 'trustops-security-data-lake[server]'"
        ) from exc
    with tempfile.TemporaryDirectory() as tmp:
        spec = create_app(tmp, require_auth=False).openapi()
    text = json.dumps(spec, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote OpenAPI schema ({len(spec.get('paths', {}))} paths): {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
