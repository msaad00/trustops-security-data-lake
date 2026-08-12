"""Connector state files must not be world-readable.

`gold/connector_config.jsonl` holds the access path for every configured
connector. Secret-shaped values are redacted before the write, but what remains
still identifies how TrustOps reaches a customer account -- role ARNs, account
ids, hosts, usernames, and the AWS External ID, which `connector_runner` reads
back from this file at sync time. At the default 0644 any local account on the
host can read all of it.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from security_lakehouse.connector_state import CONFIG_FILE, RUNS_FILE, append_config_event, append_run_event


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_config_events_are_written_owner_only(tmp_path: Path) -> None:
    append_config_event(
        tmp_path,
        connector_id="github-security",
        state="disabled",
        actor="tester",
        credentials={"token": "ghp_secret", "external_id": "ext-123"},
        options={"repo": "acme/widgets"},
    )
    path = tmp_path / "gold" / CONFIG_FILE
    assert _mode(path) == 0o600, f"connector config is {oct(_mode(path))}, expected 0600"


def test_run_events_are_written_owner_only(tmp_path: Path) -> None:
    append_run_event(tmp_path, connector_id="github-security", kind="probe", result="ok", actor="tester")
    path = tmp_path / "gold" / RUNS_FILE
    assert _mode(path) == 0o600


def test_a_file_left_world_readable_is_tightened_on_next_write(tmp_path: Path) -> None:
    """Existing installs already have 0644 files; the next write must fix them."""
    gold = tmp_path / "gold"
    gold.mkdir(parents=True)
    path = gold / CONFIG_FILE
    path.write_text("", encoding="utf-8")
    path.chmod(0o644)
    assert _mode(path) == 0o644

    append_config_event(tmp_path, connector_id="github-security", state="disabled", actor="tester")
    assert _mode(path) == 0o600


def test_append_refuses_to_follow_a_symlink(tmp_path: Path) -> None:
    """A symlink where the state file belongs must not redirect the write."""
    gold = tmp_path / "gold"
    gold.mkdir(parents=True)
    target = tmp_path / "elsewhere.jsonl"
    target.write_text("", encoding="utf-8")
    (gold / CONFIG_FILE).symlink_to(target)

    with pytest.raises(OSError):
        append_config_event(tmp_path, connector_id="github-security", state="disabled", actor="tester")
    assert target.read_text(encoding="utf-8") == ""
