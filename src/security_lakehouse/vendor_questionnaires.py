"""Bundled vendor-risk questionnaire templates and scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from security_lakehouse.catalog import _data_root

DEFAULT_VENDOR_QUESTIONNAIRES = _data_root() / "programs" / "vendor_questionnaires.json"
ANSWER_SCORES = {"yes": 1.0, "partial": 0.5, "no": 0.0}
VENDOR_RISK_LEVELS = ("low", "medium", "high", "critical")


def load_vendor_questionnaire_catalog(path: str | Path | None = None) -> dict[str, Any]:
    catalog_path = Path(path or DEFAULT_VENDOR_QUESTIONNAIRES)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    templates = payload.get("templates")
    if not isinstance(templates, list):
        raise ValueError("vendor questionnaire catalog must contain a templates list")
    return payload


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
