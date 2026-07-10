"""Reviewed control↔article mappings + new fixture sanity tests."""

from __future__ import annotations

import json
import threading
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.fixtures import find_fixture, list_fixtures
from security_lakehouse.mappings import (
    build_reviewed_crosswalk,
    load_control_article_mappings,
    validate_control_article_mappings,
)
from security_lakehouse.server import _Handler


def test_mapping_catalog_is_well_formed() -> None:
    errors = validate_control_article_mappings()
    assert errors == [], errors


def test_every_mapping_points_at_a_known_control() -> None:
    catalog = set(load_control_catalog().keys())
    for control_id in load_control_article_mappings():
        assert control_id in catalog, f"mapping references unknown control {control_id}"


def test_public_source_frameworks_have_reviewed_coverage_floor() -> None:
    catalog = load_control_catalog()
    mappings = load_control_article_mappings()
    coverage_floor = {
        "soc2": 61,
        "nist-ai-rmf": 72,
        "fedramp-moderate": 287,
        "cis_aws": 62,
        "iso-27001-2022": 93,
        "iso-42001-2023": 38,
        "hipaa-security-rule": 18,
        "gdpr-2016-679": 20,
        "eu-ai-act-2024-1689": 15,
        "pci-dss-v4": 12,
    }

    for framework_id, minimum in coverage_floor.items():
        controls = [control for control in catalog.values() if control["framework_id"] == framework_id]
        mapped = [control for control in controls if control["control_id"] in mappings]
        assert len(controls) >= minimum, f"{framework_id} should have at least {minimum} public-source controls"
        assert len(mapped) == len(controls), f"{framework_id} controls must all have reviewed source mappings"


def test_reviewed_crosswalk_returns_diagonal_and_counts() -> None:
    crosswalk = build_reviewed_crosswalk()
    fids = crosswalk["frameworks"]
    assert len(fids) >= 2
    for row in crosswalk["matrix"]:
        assert row["mapping_count"] >= 1
        assert row["article_count"] >= 1
        assert row["domain_count"] >= 1
        for cell in row["cells"]:
            if cell["framework_id"] == row["framework_id"]:
                assert cell["is_self"] is True


def test_reviewed_crosswalk_surfaces_cross_framework_domains() -> None:
    # The crosswalk's value is cross-framework overlap. article_id / control_id
    # are framework-unique so they only match on the diagonal; risk_domain is
    # the shared axis. Assert at least one off-diagonal cell shares a domain.
    crosswalk = build_reviewed_crosswalk()
    off_diagonal_with_domains = [
        cell for row in crosswalk["matrix"] for cell in row["cells"] if not cell["is_self"] and cell["shared_domains"]
    ]
    assert off_diagonal_with_domains, "crosswalk produced no cross-framework domain overlap"


def test_fintech_and_healthcare_fixtures_ship_and_validate() -> None:
    fixtures = {f.company: f for f in list_fixtures()}
    assert {"fintech", "healthcare", "golden"}.issubset(fixtures.keys())
    catalog = set(load_control_catalog().keys())
    for fixture in fixtures.values():
        for control_id in fixture.controls:
            assert control_id in catalog, f"fixture {fixture.company} references unknown control {control_id}"
        assert fixture.event_count > 0


def test_find_fixture_returns_fintech() -> None:
    fixture = find_fixture("fintech")
    assert fixture is not None
    assert "SOC2-CC6.1" in fixture.controls


def _spin(lake: Path) -> ThreadingHTTPServer:
    (lake / "console.html").write_bytes(b"<!doctype html>")
    (lake / "gold").mkdir(parents=True, exist_ok=True)
    (lake / "silver").mkdir(parents=True, exist_ok=True)

    class Handler(_Handler):
        lake_dir = lake
        dashboard_path = lake / "console.html"
        web_dist = None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _get(server: ThreadingHTTPServer, path: str) -> tuple[int, dict]:
    host, port = server.server_address
    with urllib.request.urlopen(f"http://{host}:{port}{path}") as resp:  # noqa: S310
        return int(resp.status), json.loads(resp.read().decode("utf-8"))


def test_mapping_endpoints_round_trip(tmp_path: Path) -> None:
    server = _spin(tmp_path)
    try:
        status, body = _get(server, "/api/mappings")
        assert status == HTTPStatus.OK
        assert body["count"] >= 4
        first = body["mappings"][0]
        assert "control_id" in first and "articles" in first

        status, body = _get(server, "/api/crosswalk/reviewed")
        assert status == HTTPStatus.OK
        assert "frameworks" in body and "matrix" in body
    finally:
        server.shutdown()
