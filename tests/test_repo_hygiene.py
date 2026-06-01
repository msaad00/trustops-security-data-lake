from __future__ import annotations

from pathlib import Path

# Source roots that must stay free of editor / Finder copy artifacts. Generated
# trees (node_modules, Next.js build output, the bundled web dist) are excluded.
_SOURCE_ROOTS = (
    Path("src/security_lakehouse"),
    Path("tests"),
    Path("app/web/src"),
)
_EXCLUDED_DIRS = ("node_modules", ".next", "web/dist", "__pycache__")


def _is_copy_artifact(path: Path) -> bool:
    name = path.name
    stem = path.stem
    return " copy" in name or path.suffix in {".bak", ".orig"} or any(f" {i}" in stem for i in range(2, 10))


def test_source_tree_has_no_editor_copy_artifacts() -> None:
    offenders: list[str] = []
    for root in _SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            posix = path.as_posix()
            if not path.is_file() or any(excluded in posix for excluded in _EXCLUDED_DIRS):
                continue
            if _is_copy_artifact(path):
                offenders.append(posix)
    assert offenders == [], f"editor/Finder copy artifacts found: {offenders}"
