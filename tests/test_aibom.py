"""CycloneDX/SPDX AIBOM import/export contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from security_lakehouse.ai_governance import list_ai_inventory
from security_lakehouse.aibom import aibom_status, export_aibom, import_aibom
from security_lakehouse.cli import main


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cyclonedx_import_and_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "model.cdx.json"
    _write(
        source,
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.7",
            "version": 1,
            "components": [
                {
                    "type": "machine-learning-model",
                    "bom-ref": "model:reranker:v3",
                    "name": "customer-support-reranker",
                    "version": "3",
                    "purl": "pkg:huggingface/acme/reranker@3",
                    "modelCard": {"bom-ref": "card:reranker:v3"},
                    "licenses": [{"license": {"id": "Apache-2.0"}}],
                },
                {"type": "data", "bom-ref": "data:training:v2", "name": "support-training", "version": "2"},
            ],
        },
    )
    result = import_aibom(input_path=source, lake=tmp_path / "lake")
    assert result["imported"] == 2
    assert len(result["source_sha256"]) == 64
    assert aibom_status(lake=tmp_path / "lake")["items"] == 2
    assert {row["asset_id"] for row in list_ai_inventory(lake=tmp_path / "lake")} == {
        "data:training:v2",
        "model:reranker:v3",
    }

    output = tmp_path / "export.cdx.json"
    exported = export_aibom(lake=tmp_path / "lake", output_path=output, output_format="cyclonedx-1.7")
    assert exported["exported"] == 2
    document = json.loads(output.read_text())
    assert document["specVersion"] == "1.7"
    model = next(component for component in document["components"] if component["bom-ref"] == "model:reranker:v3")
    assert model["modelCard"]["bom-ref"] == "model:reranker:v3:model-card"


def test_spdx_jsonld_import_and_export(tmp_path: Path) -> None:
    source = tmp_path / "model.spdx.json"
    _write(
        source,
        {
            "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
            "@graph": [
                {
                    "@id": "urn:spdx:acme:model:1",
                    "@type": "AI.AIPackage",
                    "name": "fraud-model",
                    "packageVersion": "1.4",
                    "description": "Transaction risk model",
                }
            ],
        },
    )
    assert import_aibom(input_path=source, lake=tmp_path / "lake")["format"] == "spdx-3.0.1"
    output = tmp_path / "export.spdx.json"
    export_aibom(lake=tmp_path / "lake", output_path=output, output_format="spdx-3.0.1")
    document = json.loads(output.read_text())
    assert document["specVersion"] == "3.0.1"
    assert document["@graph"][0]["name"] == "fraud-model"


def test_import_rejects_unbounded_or_unknown_documents(tmp_path: Path) -> None:
    source = tmp_path / "unknown.json"
    _write(source, {"components": []})
    with pytest.raises(ValueError, match="SPDX"):
        import_aibom(input_path=source, lake=tmp_path / "lake")


def test_cli_import_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "model.cdx.json"
    _write(
        source,
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "components": [{"type": "machine-learning-model", "name": "classifier"}],
        },
    )
    lake = tmp_path / "lake"
    output = tmp_path / "aibom.json"
    assert main(["aibom", "import", "--input", str(source), "--lake", str(lake)]) == 0
    assert main(["aibom", "export", "--lake", str(lake), "--out", str(output), "--format", "cyclonedx-1.7"]) == 0
    assert "cyclonedx-1.7" in capsys.readouterr().out
    assert output.exists()
