#!/usr/bin/env python3
"""Bounded synthetic SHA-256 microbenchmark; no cloud or evidence input."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

from security_lakehouse.io import file_sha256

MIB = 1024 * 1024


def worker(method: str, path: Path) -> dict:
    # Both workers import the same modules before measurement. RSS includes the
    # interpreter; tracemalloc isolates Python allocations during the hash call.
    tracemalloc.start()
    started = time.perf_counter()
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if method == "whole_file" else file_sha256(path)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "method": method,
        "sha256": digest,
        "seconds": elapsed,
        "peak_python_bytes": peak,
        "peak_rss_bytes": int(rss if sys.platform == "darwin" else rss * 1024),
    }


def benchmark(sizes: list[int], repeats: int) -> dict:
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    diff = subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=root)
    report = {
        "schema_version": "trustops.artifact_hash_benchmark.v1",
        "scope": "synthetic file hashing only; not pipeline capacity or accuracy",
        "timestamp": datetime.now(UTC).isoformat(),
        "revision": revision,
        "tracked_tree_dirty": bool(diff),
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "measured_sources": {
            name: file_sha256(root / name)
            for name in ("src/security_lakehouse/io.py", "tools/benchmark_artifact_hashing.py")
        },
        "environment": {
            "python": platform.python_version(),
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "disk_type": "not_recorded",
        },
        "protocol": {
            "cache": "warm: parent reads the file before each worker; no cold-cache measurements",
            "concurrency": 1,
            "repeats": repeats,
            "worker_timeout_seconds": 60,
            "max_fixture_mib": 256,
            "fixture": "repeated bytes 0..255; no randomness or private data",
            "order": "alternate whole-file/streaming order each repeat",
            "rss": "process lifetime peak including interpreter/imports",
            "python_memory": "tracemalloc peak during hash call",
        },
        "attempts": [],
    }
    with tempfile.TemporaryDirectory(prefix="trustops-hash-bench-") as directory:
        path = Path(directory) / "synthetic.bin"
        block = bytes(range(256)) * (MIB // 256)
        for size in sizes:
            expected = hashlib.sha256()
            with path.open("wb") as stream:
                for _ in range(size):
                    stream.write(block)
                    expected.update(block)
            for repeat in range(repeats):
                methods = ("whole_file", "streaming") if repeat % 2 == 0 else ("streaming", "whole_file")
                for method in methods:
                    file_sha256(path)
                    attempt = {"size_bytes": size * MIB, "repeat": repeat + 1, "method": method}
                    try:
                        result = subprocess.run(
                            [sys.executable, str(Path(__file__).resolve()), "--worker", method, "--input", str(path)],
                            capture_output=True,
                            text=True,
                            timeout=60,
                            check=True,
                        )
                        attempt.update(json.loads(result.stdout))
                        attempt["status"] = "measured" if attempt["sha256"] == expected.hexdigest() else "hash_mismatch"
                    except (subprocess.SubprocessError, ValueError) as exc:
                        # Preserve failed attempts without copying local paths or
                        # arbitrary process output into a publishable artifact.
                        attempt.update(status="failed", error_type=type(exc).__name__)
                    report["attempts"].append(attempt)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes-mib", nargs="+", type=int, choices=(8, 64, 256), default=[8, 64, 256])
    parser.add_argument("--repeats", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--worker", choices=("whole_file", "streaming"), help=argparse.SUPPRESS)
    parser.add_argument("--input", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.input is None:
            parser.error("worker requires an input")
        print(json.dumps(worker(args.worker, args.input)))
        return 0
    report = benchmark(args.sizes_mib, args.repeats)
    print(json.dumps(report, indent=2))
    return int(any(attempt["status"] != "measured" for attempt in report["attempts"]))


if __name__ == "__main__":
    raise SystemExit(main())
