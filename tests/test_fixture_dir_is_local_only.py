"""`fixture_dir` must not be settable over HTTP.

It points the connector runner at a directory of canned evidence instead of a
live API. Locally that is a development affordance. Over HTTP it is a file-read
primitive: the runner reads fixed filenames (`users.json`, `logs.json`, ...)
from wherever it points and ingests them into the evidence lake, where they are
readable at `read` scope.

Verified against a running server before the guard: a file planted outside the
lake reached `bronze/raw_events.jsonl` via configure + sync. That turns
`connector_manage` into host file disclosure to every reader.
"""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest

from security_lakehouse import api_v1


@pytest.mark.parametrize("action", ["configure", "discover", "probe"])
def test_fixture_dir_is_rejected_on_every_connector_write(tmp_path: Path, action: str) -> None:
    status, body = api_v1.handle_post(
        f"/api/v1/connectors/okta-identity/{action}",
        {"state": "enabled", "credentials": {"token": "t"}, "options": {"fixture_dir": "/etc"}},
        tmp_path,
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert body["errors"][0]["code"] == "bad_request"
    assert "fixture_dir" in body["errors"][0]["detail"]


def test_other_options_are_untouched(tmp_path: Path) -> None:
    """The guard must reject one key, not connector configuration generally."""
    status, body = api_v1.handle_post(
        "/api/v1/connectors/okta-identity/probe",
        {"credentials": {"token": "t", "org_url": "https://x.okta.com"}, "options": {"org": "acme"}},
        tmp_path,
    )
    assert status != HTTPStatus.BAD_REQUEST or "fixture_dir" not in str(body)


def test_local_callers_can_still_use_fixtures(tmp_path: Path) -> None:
    """The CLI and seeding paths pass fixture_dir directly and must keep working."""
    from security_lakehouse.connector_state import append_config_event

    record = append_config_event(
        tmp_path,
        connector_id="okta-identity",
        state="disabled",
        actor="cli",
        options={"fixture_dir": str(tmp_path / "fixtures")},
    )
    assert record["options"]["fixture_dir"] == str(tmp_path / "fixtures")
