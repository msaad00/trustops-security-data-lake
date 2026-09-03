"""Bundled vendor-risk questionnaire templates and scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import _data_root
from security_lakehouse.safeguards import load_safeguards

DEFAULT_VENDOR_QUESTIONNAIRES = _data_root() / "programs" / "vendor_questionnaires.json"
ANSWER_SCORES = {"yes": 1.0, "partial": 0.5, "no": 0.0}
VENDOR_RISK_LEVELS = ("low", "medium", "high", "critical")
SCHEMA_VERSION = "trustops.vendor_questionnaire.v2"
VALID_MAPPING_STATES = {"proposed", "reviewed"}


def _normalize_questionnaire_catalog(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate questionnaire-to-CCF links and derive requirement metadata."""
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"vendor questionnaire schema_version must be {SCHEMA_VERSION!r}")

    safeguards = {str(row["safeguard_id"]): row for row in load_safeguards().get("safeguards") or []}
    seen_templates: set[str] = set()
    for template in payload.get("templates") or []:
        template_id = str(template.get("template_id") or "")
        if not template_id:
            raise ValueError("vendor questionnaire template is missing template_id")
        if template_id in seen_templates:
            raise ValueError(f"duplicate vendor questionnaire template_id {template_id!r}")
        seen_templates.add(template_id)

        seen_sections: set[str] = set()
        seen_questions: set[str] = set()
        template_safeguards: set[str] = set()
        template_risk_domains: set[str] = set()
        template_frameworks: set[str] = set()
        template_controls: set[str] = set()
        mapped_questions = 0

        for section in template.get("sections") or []:
            section_id = str(section.get("section_id") or "")
            if not section_id or section_id in seen_sections:
                raise ValueError(f"{template_id}: missing or duplicate section_id {section_id!r}")
            seen_sections.add(section_id)
            for question in section.get("questions") or []:
                question_id = str(question.get("question_id") or "")
                context = f"{template_id}/{section_id}/{question_id or '<missing>'}"
                if not question_id or question_id in seen_questions:
                    raise ValueError(f"{context}: missing or duplicate question_id")
                seen_questions.add(question_id)

                mapping_status = str(question.get("mapping_status") or "")
                if mapping_status not in VALID_MAPPING_STATES:
                    raise ValueError(f"{context}: invalid mapping_status {mapping_status!r}")
                safeguard_ids = question.get("safeguard_ids")
                if not isinstance(safeguard_ids, list) or not safeguard_ids:
                    raise ValueError(f"{context}: safeguard_ids must be a non-empty list")

                question_risk_domains: set[str] = set()
                question_frameworks: set[str] = set()
                question_controls: set[str] = set()
                for safeguard_id in safeguard_ids:
                    safeguard = safeguards.get(str(safeguard_id))
                    if safeguard is None:
                        raise ValueError(f"{context}: unknown safeguard_id {safeguard_id!r}")
                    template_safeguards.add(str(safeguard_id))
                    risk_domain = str(safeguard.get("risk_domain") or "")
                    if risk_domain:
                        question_risk_domains.add(risk_domain)
                    for mapping in safeguard.get("satisfies") or []:
                        control_id = str(mapping.get("control_id") or "")
                        framework_id = str(mapping.get("framework_id") or "")
                        if control_id:
                            question_controls.add(control_id)
                        if framework_id:
                            question_frameworks.add(framework_id)

                question["risk_domains"] = sorted(question_risk_domains)
                question["framework_ids"] = sorted(question_frameworks)
                question["control_ids"] = sorted(question_controls)
                template_risk_domains.update(question_risk_domains)
                template_frameworks.update(question_frameworks)
                template_controls.update(question_controls)
                mapped_questions += 1

        template["mapping_status"] = (
            "reviewed"
            if all(
                question.get("mapping_status") == "reviewed"
                for section in template.get("sections") or []
                for question in section.get("questions") or []
            )
            else "proposed"
        )
        template["mapped_question_count"] = mapped_questions
        template["safeguard_ids"] = sorted(template_safeguards)
        template["risk_domains"] = sorted(template_risk_domains)
        template["framework_ids"] = sorted(template_frameworks)
        template["control_ids"] = sorted(template_controls)
    return payload


def load_vendor_questionnaire_catalog(path: str | Path | None = None) -> dict[str, Any]:
    catalog_path = Path(path or DEFAULT_VENDOR_QUESTIONNAIRES)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    templates = payload.get("templates")
    if not isinstance(templates, list):
        raise ValueError("vendor questionnaire catalog must contain a templates list")
    return _normalize_questionnaire_catalog(payload)


def list_vendor_questionnaire_templates(path: str | Path | None = None) -> list[dict[str, Any]]:
    return list(load_vendor_questionnaire_catalog(path).get("templates") or [])


def get_vendor_questionnaire_template(template_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    for template in list_vendor_questionnaire_templates(path):
        if str(template.get("template_id") or "") == template_id:
            return template
    return None


def iter_template_questions(template: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in template.get("sections") or []:
        section_id = str(section.get("section_id") or "")
        for question in section.get("questions") or []:
            rows.append({**question, "section_id": section_id, "section_title": section.get("title") or ""})
    return rows


def score_vendor_responses(
    template: dict[str, Any],
    responses: dict[str, Any],
) -> dict[str, Any]:
    """Score questionnaire responses into a 0-100 vendor readiness score."""
    total_weight = 0.0
    earned = 0.0
    answered = 0
    required_missing: list[str] = []
    for question in iter_template_questions(template):
        qid = str(question.get("question_id") or "")
        weight = float(question.get("weight") or 1)
        required = bool(question.get("required"))
        raw = responses.get(qid)
        answer = ""
        if isinstance(raw, dict):
            answer = str(raw.get("answer") or "").strip().lower()
        elif isinstance(raw, str):
            answer = raw.strip().lower()
        if not answer:
            if required:
                required_missing.append(qid)
            continue
        if answer == "na":
            continue
        if answer not in ANSWER_SCORES:
            raise ValueError(f"invalid answer for {qid}: {answer!r}")
        total_weight += weight
        earned += weight * ANSWER_SCORES[answer]
        answered += 1
    if required_missing:
        raise ValueError(f"missing required answers: {', '.join(required_missing)}")
    score = round((earned / total_weight) * 100, 2) if total_weight else 0.0
    return {
        "score": score,
        "risk_level": risk_level_for_score(score),
        "answered_count": answered,
        "question_count": len(iter_template_questions(template)),
    }


def risk_level_for_score(score: float) -> str:
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "high"
    return "critical"
