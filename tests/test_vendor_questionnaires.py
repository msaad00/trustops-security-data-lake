"""Vendor questionnaire catalog and scoring."""

from __future__ import annotations

import pytest

from security_lakehouse.vendor_questionnaires import (
    get_vendor_questionnaire_template,
    iter_template_questions,
    list_vendor_questionnaire_templates,
    load_vendor_questionnaire_catalog,
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


def test_catalog_normalizes_questions_to_ccf_and_framework_requirements(template: dict) -> None:
    catalog = load_vendor_questionnaire_catalog()
    assert catalog["schema_version"] == "trustops.vendor_questionnaire.v2"

    questions = iter_template_questions(template)
    assert len(questions) == 10
    assert all(question["mapping_status"] == "proposed" for question in questions)
    assert all(question["safeguard_ids"] for question in questions)
    assert all(question["risk_domains"] for question in questions)
    assert all(question["framework_ids"] for question in questions)
    assert all(question["control_ids"] for question in questions)

    mfa = next(question for question in questions if question["question_id"] == "mfa")
    assert mfa["safeguard_ids"] == ["SG-IDENTITY-001"]
    assert mfa["risk_domains"] == ["identity"]
    assert {"soc2", "iso-27001-2022", "fedramp-moderate", "cmmc-2-level2"} <= set(mfa["framework_ids"])


def test_catalog_rejects_unknown_safeguard_mapping(tmp_path) -> None:
    source = load_vendor_questionnaire_catalog()
    source["templates"][0]["sections"][0]["questions"][0]["safeguard_ids"] = ["SG-NOT-REAL"]
    path = tmp_path / "vendor_questionnaires.json"
    path.write_text(__import__("json").dumps(source), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown safeguard_id 'SG-NOT-REAL'"):
        load_vendor_questionnaire_catalog(path)


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
