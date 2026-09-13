"""Controls-as-code policy engine tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from security_lakehouse.controls import DEFAULT_CATALOG_PATH
from security_lakehouse.policy import (
    NAMED_RULES,
    ControlContext,
    PolicyError,
    evaluate_control,
    validate_rule,
)


def _ctx(**kwargs) -> ControlContext:
    base = {"control_id": "C1", "event_count": 1, "evidence_count": 1}
    return ControlContext(**{**base, **kwargs})


def test_default_rule_fails_on_open_violation() -> None:
    result = evaluate_control(_ctx(open_violation_count=1), None)
    assert result.status == "fail"
    assert result.rule == "fail_when_open_violation"
    assert result.reasons


def test_default_rule_passes_when_clean() -> None:
    result = evaluate_control(_ctx(open_violation_count=0), None)
    assert result.status == "pass"
    assert result.reasons == []


def test_stale_evidence_rules_fail_on_stale() -> None:
    for rule in ("fail_when_stale_evidence", "fail_when_open_violation_or_stale_evidence"):
        assert evaluate_control(_ctx(open_violation_count=0, evidence_status="stale"), rule).status == "fail"
        assert evaluate_control(_ctx(open_violation_count=0, evidence_status="fresh"), rule).status == "pass"
        assert evaluate_control(_ctx(open_violation_count=2, evidence_status="fresh"), rule).status == "fail"


def test_high_severity_rule_needs_both_open_and_severity() -> None:
    rule = "fail_when_high_severity_open"
    assert evaluate_control(_ctx(open_violation_count=1, max_severity="high"), rule).status == "fail"
    assert evaluate_control(_ctx(open_violation_count=1, max_severity="low"), rule).status == "pass"
    assert evaluate_control(_ctx(open_violation_count=0, max_severity="critical"), rule).status == "pass"


def test_missing_evidence_rule() -> None:
    rule = "fail_when_missing_evidence"
    assert evaluate_control(_ctx(open_violation_count=0, evidence_count=0), rule).status == "fail"
    assert evaluate_control(_ctx(open_violation_count=0, evidence_count=3), rule).status == "pass"


def test_inline_spec_with_any_all_not() -> None:
    rule = {"fail_if": {"all": [{"open_violations": {"min": 1}}, {"not": {"evidence_present": True}}]}}
    assert evaluate_control(_ctx(open_violation_count=1, evidence_count=0), rule).status == "fail"
    assert evaluate_control(_ctx(open_violation_count=1, evidence_count=2), rule).status == "pass"


def test_min_evidence_coverage_leaf() -> None:
    rule = {"fail_if": {"min_evidence_coverage": {"below": 0.5}}}
    assert evaluate_control(_ctx(event_count=4, evidence_count=1), rule).status == "fail"
    assert evaluate_control(_ctx(event_count=4, evidence_count=3), rule).status == "pass"


@pytest.mark.parametrize(
    "rule",
    [
        "typo-invalid-rule",
        {"fail_if": {"open_violations": {"min": "bad"}}},
        {"fail_if": {"evidence_present": "false"}},
        {"fail_if": {"all": []}},
        {"fail_if": {"any": 1}},
        {"fail_if": {"max_severity": {"at_least": "typo"}}},
        {"fail_if": {"open_violations": {"minimum": 1}}},
        {"fail_if": {"evidence_present": True, "unknown": False}},
        {"fail_if": {"evidence_present": True}, "unknown": False},
    ],
)
def test_invalid_rule_stops_evaluation(rule) -> None:
    assert validate_rule(rule)
    with pytest.raises(PolicyError):
        evaluate_control(_ctx(open_violation_count=0), rule)


def test_validate_rule_catches_bad_specs() -> None:
    assert validate_rule("fail_when_open_violation") == []
    assert validate_rule({"fail_if": {"open_violations": {"min": 1}}}) == []
    assert validate_rule("nope")
    assert validate_rule({"fail_if": {"bogus_leaf": 1}})
    assert validate_rule({"no_fail_if": {}})


def test_named_rules_are_all_self_valid() -> None:
    for name in NAMED_RULES:
        assert validate_rule(name) == []


def test_catalog_rules_all_known() -> None:
    """Every evaluation_rule shipped in the catalog must be defined (lint gate)."""
    catalog = json.loads(Path(DEFAULT_CATALOG_PATH).read_text(encoding="utf-8"))
    problems = [
        f"{c.get('control_id')}: {p}" for c in catalog["controls"] for p in validate_rule(c.get("evaluation_rule"))
    ]
    assert problems == [], problems
