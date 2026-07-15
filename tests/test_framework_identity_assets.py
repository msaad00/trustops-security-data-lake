from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITIES = ROOT / "frameworks" / "identity-assets.json"
REGISTRY = ROOT / "frameworks" / "registry.json"


def test_every_registered_framework_has_a_governed_identity() -> None:
    registered = {
        row["framework_id"] for row in json.loads(REGISTRY.read_text())["frameworks"]
    }
    identities = json.loads(IDENTITIES.read_text())["frameworks"]

    assert set(identities) == registered
    assert all(row["official_name"] for row in identities.values())
    assert all(row["official_source_url"].startswith("https://") for row in identities.values())


def test_bundled_official_artwork_has_verifiable_permission_and_integrity() -> None:
    identities = json.loads(IDENTITIES.read_text())["frameworks"]
    official = {
        framework_id: row
        for framework_id, row in identities.items()
        if row["display_mode"] == "official_artwork"
    }

    assert set(official) == {"nist-ai-rmf", "nist-csf-2.0"}
    for row in official.values():
        asset = ROOT / row["asset_path"]
        assert asset.is_file()
        assert hashlib.sha256(asset.read_bytes()).hexdigest() == row["sha256"]
        assert row["asset_source_url"].startswith("https://www.nist.gov/")
        assert row["usage_terms_url"] == "https://www.nist.gov/copyrights-disclaimers"
        assert row["attribution"]
        assert row["endorsement_disclaimer"]


def test_restricted_marks_fall_back_without_bundled_assets() -> None:
    identities = json.loads(IDENTITIES.read_text())["frameworks"]

    for row in identities.values():
        if row["display_mode"] == "neutral_icon":
            assert row["asset_path"] is None
            assert row["restriction"]
