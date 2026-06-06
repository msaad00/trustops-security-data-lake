"""First-class `stale` control status.

A control with no fresh evidence inside its freshness SLO is `stale` — not a
silent `pass` and not a `fail`. An open violation always dominates.
"""

from __future__ import annotations

from security_lakehouse.pipeline import _build_control_rows

CONTROL_MAP = {
    "C1": {
        "control_id": "C1",
        "framework": "SOC 2",
        "title": "Logical access",
        "risk_domain": "identity",
        "owner": "security",
        "evaluation_rule": "fail_when_open_violation_or_stale_evidence",
    }
}


def _silver(*, status: str = "ok", evidence: str = "ev-1", severity: str = "info", score: int = 0) -> dict:
    return {
        "control_ids": ["C1"],
        "status": status,
        "evidence_ref": evidence,
        "severity": severity,
        "severity_score": score,
        "event_time": "2026-06-01T00:00:00Z",
    }


def test_stale_when_evidence_outside_freshness_slo() -> None:
    rows = _build_control_rows([_silver()], CONTROL_MAP, stale_controls={"C1"})
    assert rows[0]["status"] == "stale"


def test_pass_when_fresh_and_compliant() -> None:
    rows = _build_control_rows([_silver()], CONTROL_MAP, stale_controls=set())
    assert rows[0]["status"] == "pass"


def test_no_evidence_at_all_is_stale() -> None:
    rows = _build_control_rows([_silver(evidence="")], CONTROL_MAP, stale_controls=set())
    assert rows[0]["status"] == "stale"


def test_open_violation_dominates_stale() -> None:
    rows = _build_control_rows(
        [_silver(status="open", severity="high", score=80)],
        CONTROL_MAP,
        stale_controls={"C1"},
    )
    assert rows[0]["status"] == "fail"
