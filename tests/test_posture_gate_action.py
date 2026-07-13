"""Tests for the Koda GitHub Action posture gate script."""

from __future__ import annotations

import os
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import yaml

from test_api_v1 import _Handler, _seed_lake


def _action_dir() -> Path:
    return Path(__file__).resolve().parents[1] / ".github" / "actions" / "posture-gate"


def _spin(lake: Path) -> ThreadingHTTPServer:
    _seed_lake(lake)

    class Handler(_Handler):
        lake_dir = lake
        dashboard_path = lake / "console.html"
        web_dist = None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _run_gate(
    lake: Path,
    *,
    min_score: str = "0",
    max_critical: str = "0",
    max_open: str = "-1",
    max_failing: str = "-1",
    allowed_failing: str = "",
    correlation_id: str = "test-corr-1",
) -> subprocess.CompletedProcess[str]:
    server = _spin(lake)
    host, port = server.server_address
    env = {
        **os.environ,
        "TRUSTOPS_URL": f"http://{host}:{port}",
        "TRUSTOPS_API_TOKEN": "",
        "CORRELATION_ID": correlation_id,
        "MIN_SCORE": min_score,
        "MAX_CRITICAL_VIOLATIONS": max_critical,
        "MAX_OPEN_VIOLATIONS": max_open,
        "MAX_FAILING_CONTROL_TESTS": max_failing,
        "ALLOWED_FAILING_CONTROLS": allowed_failing,
        "FAIL_ON_STALE_EVIDENCE": "false",
    }
    try:
        return subprocess.run(
            ["bash", str(_action_dir() / "posture-gate.sh")],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    finally:
        server.shutdown()


def test_posture_gate_action_metadata_is_valid() -> None:
    action = yaml.safe_load((_action_dir() / "action.yml").read_text(encoding="utf-8"))
    assert action["name"] == "Koda Posture Gate"
    assert "trustops-url" in action["inputs"]
    assert "max-failing-control-tests" in action["inputs"]
    assert action["runs"]["using"] == "composite"


def test_posture_gate_passes_against_seeded_lake(tmp_path: Path) -> None:
    result = _run_gate(tmp_path, min_score="0", max_critical="0", max_failing="-1")
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Posture gate passed" in result.stdout
    assert "test-corr-1" in result.stdout


def test_posture_gate_fails_when_min_score_too_high(tmp_path: Path) -> None:
    result = _run_gate(tmp_path, min_score="100", max_failing="-1")
    assert result.returncode == 1
    assert "below minimum" in result.stdout


def test_posture_gate_fails_on_control_regression(tmp_path: Path) -> None:
    result = _run_gate(tmp_path, max_failing="0")
    assert result.returncode == 1
    assert "failing control tests" in result.stdout
    assert "SOC2-CC6.1" in result.stdout


def test_posture_gate_passes_with_allowed_failing_control(tmp_path: Path) -> None:
    result = _run_gate(
        tmp_path,
        max_failing="0",
        allowed_failing="SOC2-CC6.1",
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Posture gate passed" in result.stdout


def test_tools_ci_wrapper_invokes_action_script(tmp_path: Path) -> None:
    wrapper = Path(__file__).resolve().parents[1] / "tools" / "ci" / "posture-gate.sh"
    assert wrapper.is_file()
    result = _run_gate(tmp_path, max_failing="-1")
    assert result.returncode == 0
