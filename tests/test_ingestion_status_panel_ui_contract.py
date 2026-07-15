"""UI contract for keeping probes separate from evidence activity."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
PANEL = ROOT / "app/web/src/components/dashboard/IngestionStatusPanel.tsx"


def test_source_health_shows_evidence_activity_not_probe_noise() -> None:
    panel = PANEL.read_text(encoding="utf-8")

    assert "const recentEvidenceSyncs" in panel
    assert 'run.kind === "sync"' in panel
    assert "run.evidence_count ?? 0" in panel
    assert "Recent evidence syncs" in panel
    assert "Recent connector runs" not in panel


def test_source_health_lists_sources_that_landed_evidence() -> None:
    panel = PANEL.read_text(encoding="utf-8")

    assert "Evidence sources" in panel
    assert "Active sources" not in panel
    assert "connector.last_sync_at ||" in panel
    assert 'connector.state === "enabled"' not in panel
