"""Common Control Framework: safeguards as the operated object."""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.catalog import load_control_catalog
from security_lakehouse.safeguards import (
    SCHEMA,
    coverage_by_framework,
    load_safeguards,
    requirement_status,
    safeguards_by_requirement,
    validate_safeguards,
)


def test_shipped_safeguards_are_internally_consistent() -> None:
    problems = validate_safeguards(load_safeguards())
    assert problems == [], f"shipped CCF is inconsistent: {problems}"


def test_every_mapped_requirement_exists_in_the_catalog() -> None:
    """A safeguard pointing at a control_id that does not exist claims coverage it has not got."""
    known = set(load_control_catalog())
    unknown = sorted(set(safeguards_by_requirement()) - known)
    assert unknown == []


def test_each_safeguard_names_exactly_one_primary() -> None:
    for entry in load_safeguards()["safeguards"]:
        primaries = [m for m in entry["satisfies"] if m.get("role") == "primary"]
        assert len(primaries) == 1, f"{entry['safeguard_id']} has {len(primaries)} primaries"


def test_a_requirement_needing_two_safeguards_fails_when_either_fails() -> None:
    """SOC2 CC7.2 wants detection *and* audit logging.

    Treating "any mapped safeguard passes" as sufficient would let a green logging
    safeguard report the monitoring requirement as met, which is the failure mode
    a CCF exists to prevent.
    """
    mapping = safeguards_by_requirement()
    shared = [cid for cid, sids in mapping.items() if len(sids) > 1]
    assert shared, "expected at least one requirement satisfied by multiple safeguards"

    control_id = shared[0]
    sids = mapping[control_id]
    assert requirement_status(control_id, dict.fromkeys(sids, "pass")) == "pass"

    one_failing = dict.fromkeys(sids, "pass")
    one_failing[sids[0]] = "fail"
    assert requirement_status(control_id, one_failing) == "fail"


def test_an_unmapped_requirement_is_not_reported_as_failing() -> None:
    """ "Not modelled yet" and "tested and failed" are different answers to an auditor."""
    unmapped = sorted(set(load_control_catalog()) - set(safeguards_by_requirement()))
    assert unmapped, "expected uncovered controls while the CCF is partial"
    assert requirement_status(unmapped[0], {}) == "unmapped"


def test_coverage_matches_a_direct_count() -> None:
    controls = load_control_catalog()
    mapped = set(safeguards_by_requirement())
    cov = coverage_by_framework()
    assert cov["controls"] == len(controls)
    assert cov["covered"] == len(mapped & set(controls))
    assert cov["covered"] + cov["uncovered"] == cov["controls"]


def test_validation_rejects_a_safeguard_claiming_an_unknown_control(tmp_path: Path) -> None:
    payload = json.loads(json.dumps(load_safeguards()))
    payload["safeguards"][0]["satisfies"].append(
        {"control_id": "NOT-A-REAL-CONTROL", "framework_id": "soc2", "role": "equivalent"}
    )
    problems = validate_safeguards(payload)
    assert any("NOT-A-REAL-CONTROL" in p for p in problems)


def test_validation_rejects_a_wrong_schema_marker() -> None:
    payload = json.loads(json.dumps(load_safeguards()))
    payload["schema"] = "something.else.v9"
    assert any(SCHEMA in p for p in validate_safeguards(payload))


def test_the_ccf_doc_quotes_the_numbers_the_data_actually_reports() -> None:
    """The README once claimed 741 controls while the catalog held 942.

    Coverage figures in prose drift the moment curation moves, and a compliance
    product overstating its own coverage is exactly the wrong failure. Pin them.
    """
    doc = (Path(__file__).resolve().parents[1] / "docs" / "COMMON_CONTROL_FRAMEWORK.md").read_text(encoding="utf-8")
    cov = coverage_by_framework()

    headline = f"{cov['safeguards']} safeguards cover {cov['covered']} of {cov['controls']} requirements"
    assert headline in doc, f"doc headline is stale; expected {headline!r}"

    for name, row in cov["frameworks"].items():
        expected = f"| {name:19s} | {row['controls']:12d} |"
        assert expected in doc, f"doc table row for {name} is stale; expected {expected!r}"
