"""Brand compliance guard — no competitor names in public copy."""

from __future__ import annotations

from tools.check_brand_compliance import main


def test_brand_compliance_passes() -> None:
    assert main() == 0
