"""Guard against dev scaffold copy leaking into shipped source trees.

Early scaffold work left "Coming in PR N" / "PR N adds ..." placeholder copy in
user-facing surfaces (the React workbench, agent skills, the Python server).
This test greps the shipped source trees for those phrases and fails if any
remain, so the copy cannot regress. Generated trees (node_modules, the Next.js
build output, the bundled web dist) are excluded.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Shipped source trees that reach users (skills, web app, Python server).
_SOURCE_ROOTS = (
    Path("src/security_lakehouse"),
    Path("app/web/src"),
    Path("agent-skills"),
)

_EXCLUDED_DIRS = ("node_modules", ".next", "web/dist", "web-dist", "__pycache__")

_TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".mdx", ".json"}

# Scaffold phrases that must never ship to users. These are roadmap-style
# placeholders ("Coming in PR 2", "PR 3 adds drawers") that narrate unshipped
# work to the end user — distinct from a module docstring noting which PR
# introduced a code path.
_SCAFFOLD_PATTERNS = (
    re.compile(r"Coming in PR", re.IGNORECASE),
    re.compile(r"PR \d+ (adds|wires|will add|will wire)", re.IGNORECASE),
    re.compile(r"wires this to a real", re.IGNORECASE),
    re.compile(r"for now we synthesi[sz]e", re.IGNORECASE),
    re.compile(r"scaffolding only", re.IGNORECASE),
)


def test_no_scaffold_copy_in_shipped_sources() -> None:
    offenders: list[str] = []
    for root in _SOURCE_ROOTS:
        abs_root = _REPO_ROOT / root
        if not abs_root.exists():
            continue
        for path in abs_root.rglob("*"):
            posix = path.as_posix()
            if not path.is_file() or path.suffix not in _TEXT_SUFFIXES:
                continue
            if any(excluded in posix for excluded in _EXCLUDED_DIRS):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                for pattern in _SCAFFOLD_PATTERNS:
                    if pattern.search(line):
                        rel = path.relative_to(_REPO_ROOT).as_posix()
                        offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert offenders == [], "scaffold copy must not ship to users:\n" + "\n".join(offenders)
