"""SPRS scoring tests."""

from __future__ import annotations

from security_lakehouse.sprs import SPRS_BASE_SCORE, SPRS_MIN_SCORE, compute_sprs_score


def test_sprs_perfect_score_when_all_requirements_met() -> None:
    report = compute_sprs_score(failing_requirement_ids=set())
    assert report["score"] == SPRS_BASE_SCORE
    assert report["deduction_total"] == 0
    assert report["requirements_unmet"] == 0


def test_sprs_deducts_weighted_points_for_failures() -> None:
    report = compute_sprs_score(failing_requirement_ids={"3.1.1", "3.1.3"})
    assert report["deduction_total"] == 5 + 1
    assert report["score"] == SPRS_BASE_SCORE - 6
    assert len(report["deductions"]) == 2


def test_sprs_score_floors_at_minimum() -> None:
    from security_lakehouse.sprs import _cmmc_sprs_metadata

    all_failing = set(_cmmc_sprs_metadata().keys())
    report = compute_sprs_score(failing_requirement_ids=all_failing)
    assert report["score"] >= SPRS_MIN_SCORE
    assert report["requirements_unmet"] == 110
