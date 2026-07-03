"""Helm chart security guards for auth and HA."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm not installed")

CHART = Path(__file__).resolve().parents[1] / "deploy" / "helm" / "trustops"


def _helm_template(extra_sets: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = ["helm", "template", "trustops", str(CHART)]
    for item in extra_sets or []:
        cmd.extend(["--set", item])
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_insecure_no_auth_requires_acknowledged_override() -> None:
    result = _helm_template(["security.allowInsecureNoAuth=true"])
    assert result.returncode != 0
    assert "allowInsecureOverride=acknowledged" in result.stderr


def test_insecure_no_auth_passes_with_acknowledged_override() -> None:
    result = _helm_template(
        [
            "security.allowInsecureNoAuth=true",
            "security.allowInsecureOverride=acknowledged",
        ]
    )
    assert result.returncode == 0
    assert "TRUSTOPS_ALLOW_INSECURE_NO_AUTH" in result.stdout


def test_ingress_requires_auth_configuration() -> None:
    result = _helm_template(["ingress.enabled=true"])
    assert result.returncode != 0
    assert "ingress.enabled requires authentication" in result.stderr


def test_ingress_passes_with_session_secret() -> None:
    result = _helm_template(
        [
            "ingress.enabled=true",
            "env[0].name=TRUSTOPS_SESSION_SECRET",
            "env[0].value=super-secret-for-tests",
        ]
    )
    assert result.returncode == 0


def test_multi_replica_rwo_lake_blocked_without_read_only() -> None:
    result = _helm_template(["replicaCount=2"])
    assert result.returncode != 0
    assert "replicaCount > 1 with ReadWriteOnce lake" in result.stderr


def test_multi_replica_allowed_with_read_only_lake() -> None:
    result = _helm_template(["replicaCount=2", "lake.readOnly=true"])
    assert result.returncode == 0
    assert "readOnly: true" in result.stdout
