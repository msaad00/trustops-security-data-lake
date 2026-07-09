"""CLI scaffold for in-repo connector adapters."""

from __future__ import annotations

import json
from pathlib import Path

from security_lakehouse.cli import main


def test_connectors_scaffold_writes_starter_files(tmp_path: Path, capsys) -> None:
    output = tmp_path / "out"
    code = main(["connectors", "scaffold", "acme-audit-export", "--output", str(output)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["module_path"].endswith("connectors_acme_audit_export.py")
    assert Path(payload["module_path"]).is_file()
    assert Path(payload["test_path"]).is_file()
    assert "acme-audit-export" in payload["registry_line"]
    assert "is_implemented" in payload["catalog_flag"]
