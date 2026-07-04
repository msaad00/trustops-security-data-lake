"""Shared pytest configuration."""

from __future__ import annotations

import os

# Signed session cookies are mandatory whenever server auth is enabled.
os.environ.setdefault("TRUSTOPS_COOKIE_SIGNING_KEY", "test-cookie-signing-key-for-pytest-only")
