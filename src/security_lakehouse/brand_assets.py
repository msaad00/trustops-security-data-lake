"""TrustOps brand assets for MCP, HTTP, and packaging.

Icons follow MCP SEP-973 (``Implementation.icons`` and per-tool ``icons``).
Embedded SVG data URIs work for stdio transport; hosted servers also expose
``GET /brand/trustops-mark.svg`` for remote clients.
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp.types import Icon

BRAND_NAME = "TrustOps"
MCP_SERVER_NAME = "trustops"
MCP_SERVER_TITLE = "TrustOps"
MCP_INSTRUCTIONS = (
    "Headless trust operations over your evidence lake — posture, controls, "
    "evidence, violations, snapshots, workflows, audit readiness, and governed "
    "agent harness runs. Same contract as TrustOps Console and /api/v1."
)
MCP_WEBSITE_URL = "https://github.com/msaad00/trustops-security-data-lake"

# 32×32 lake-contour mark — matches the web favicon and docs lockup.
TRUSTOPS_MARK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" role="img" aria-label="TrustOps">
  <defs>
    <linearGradient id="t" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#4f7cff"/>
      <stop offset="100%" stop-color="#30c7d2"/>
    </linearGradient>
  </defs>
  <rect width="32" height="32" rx="8" fill="#071426"/>
  <g fill="none" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4.5 7.7h4.7a1.5 1.5 0 0 0 .1-3 2.2 2.2 0 0 0-4.1.6 1.25 1.25 0 0 0-.7 2.4" stroke="#4f7cff"/>
    <path d="M16 3.7c.2 1.6.9 2.4 2.5 2.6-1.6.2-2.3 1-2.5 2.6-.2-1.6-.9-2.4-2.5-2.6 1.6-.2 2.3-1 2.5-2.6Z" fill="#30c7d2" stroke="#30c7d2"/>
    <circle cx="25.5" cy="4.7" r="1.15" stroke="#5eead4"/>
    <path d="M22.8 8.5c.5-1.35 1.4-2 2.7-2s2.2.65 2.7 2" stroke="#5eead4"/>
  </g>
  <path d="M5 10c3.2-2.4 6.8-2.4 10.6 0s7.2 2.4 11.4 0M5 16c3.2-2.4 6.8-2.4 10.6 0s7.2 2.4 11.4 0" fill="none" stroke="url(#t)" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M5 22c3.2-2.4 6.8-2.4 10.6 0s7.2 2.4 11.4 0" fill="none" stroke="#5eead4" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""


@lru_cache(maxsize=1)
def trustops_mark_data_uri() -> str:
    """Return an embedded SVG data URI for offline / stdio MCP clients."""
    encoded = base64.b64encode(TRUSTOPS_MARK_SVG.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def resolve_public_api_base_url() -> str | None:
    """Best-effort public base URL for hosted icon links (MCP + OpenGraph)."""
    explicit = os.environ.get("TRUSTOPS_PUBLIC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    api_url = os.environ.get("TRUSTOPS_API_URL", "").strip().rstrip("/")
    return api_url or None


def mcp_icons() -> list[Icon]:
    """Build MCP Icon list with hosted URL (when configured) plus embedded fallback."""
    from mcp.types import Icon

    icons: list[Icon] = []
    base_url = resolve_public_api_base_url()
    if base_url:
        icons.append(
            Icon(
                src=f"{base_url}/brand/trustops-mark.svg",
                mimeType="image/svg+xml",
                sizes=["48x48", "96x96", "any"],
            )
        )
    icons.append(
        Icon(
            src=trustops_mark_data_uri(),
            mimeType="image/svg+xml",
            sizes=["any"],
        )
    )
    return icons


def human_tool_title(tool_name: str) -> str:
    """Convert ``get_posture`` → ``Get Posture`` for MCP client display."""
    return tool_name.replace("_", " ").strip().title()
