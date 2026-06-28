"""React (Next.js static export) assessment console.

`npm --prefix app/web run build` populates the ``dist`` directory below with
the compliance-grade workbench. dashboard.py and server.py prefer it when
present and fall back to the legacy single-file template otherwise.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def web_dist_dir() -> Path:
    """Return the Next.js static export directory bundled with the package."""
    return Path(str(files(__name__).joinpath("dist")))


def web_dist_index() -> Path | None:
    """Return the React app's entry HTML if the build was packaged, else None."""
    candidate = web_dist_dir() / "index.html"
    return candidate if candidate.is_file() else None
