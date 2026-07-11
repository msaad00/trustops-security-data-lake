"""Shared Pydantic bases for server request bodies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Reject unknown fields so misnamed agent payloads fail with 422."""

    model_config = ConfigDict(extra="forbid")
