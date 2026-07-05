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

# 32×32 monogram — matches app/web/src/app/icon.svg and docs/images/trustops-logo.svg
TRUSTOPS_MARK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" role="img" aria-label="TrustOps">
  <defs>
    <linearGradient id="t" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#4f7cff"/>
      <stop offset="100%" stop-color="#30c7d2"/>
    </linearGradient>
  </defs>
  <rect width="32" height="32" rx="8" fill="url(#t)"/>
  <path d="M8 9h16v4.2h-5.9V26h-4.2V13.2H8z" fill="#fff"/>
  <circle cx="24" cy="24" r="7" fill="#fff"/>
  <path d="M20.5 24l2 2 4.5-4.5" stroke="#047857" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
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
