#!/usr/bin/env python3
"""Fail CI when markdown references missing image assets."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_ROOTS = (ROOT / "README.md", ROOT / "docs")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _markdown_files() -> list[Path]:
    files = []
    if (ROOT / "README.md").is_file():
        files.append(ROOT / "README.md")
    files.extend(sorted((ROOT / "docs").rglob("*.md")))
    return files


def main() -> int:
    missing: list[str] = []
    for md_path in _markdown_files():
        text = md_path.read_text(encoding="utf-8")
        for match in IMAGE_PATTERN.finditer(text):
            target = match.group(1).strip()
            if target.startswith("http://") or target.startswith("https://"):
                continue
            asset = (md_path.parent / target).resolve()
            if not asset.is_file():
                missing.append(f"{md_path.relative_to(ROOT)} -> {target}")
    if missing:
        print("Missing markdown image assets:")
        for line in missing:
            print(f"  - {line}")
        return 1
    print(f"markdown image check passed ({len(_markdown_files())} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
