"""Vendor questionnaire catalog and scoring."""

from __future__ import annotations

import pytest

from security_lakehouse.vendor_questionnaires import (
    get_vendor_questionnaire_template,
    list_vendor_questionnaire_templates,
    risk_level_for_score,
    score_vendor_responses,
)


@pytest.fixture
def template() -> dict:
    row = get_vendor_questionnaire_template("soc2-vendor-standard")
    assert row is not None
    return row


def test_catalog_lists_soc2_template() -> None:
    templates = list_vendor_questionnaire_templates()
    ids = {row["template_id"] for row in templates}
    assert "soc2-vendor-standard" in ids


def test_all_yes_scores_low_risk(template: dict) -> None:
    responses = {q["question_id"]: {"answer": "yes"} for section in template["sections"] for q in section["questions"]}
    scored = score_vendor_responses(template, responses)
    assert scored["score"] == 100.0
    assert scored["risk_level"] == "low"


def test_all_no_scores_critical(template: dict) -> None:
    responses = {
        q["question_id"]: {"answer": "no"}
        for section in template["sections"]
        for q in section["questions"]
        if q.get("required")
    }
    scored = score_vendor_responses(template, responses)
    assert scored["score"] == 0.0
    assert scored["risk_level"] == "critical"


def test_na_skips_optional_weight(template: dict) -> None:
    responses = {
        q["question_id"]: {"answer": "yes"}
        for section in template["sections"]
        for q in section["questions"]
        if q.get("required")
    }
    responses["subprocessors"] = {"answer": "na"}
    scored = score_vendor_responses(template, responses)
    assert scored["score"] == 100.0


def test_missing_required_raises(template: dict) -> None:
    with pytest.raises(ValueError, match="missing required"):
        score_vendor_responses(template, {})


def test_risk_level_thresholds() -> None:
    assert risk_level_for_score(85) == "low"
    assert risk_level_for_score(70) == "medium"
    assert risk_level_for_score(50) == "high"
    assert risk_level_for_score(10) == "critical"
