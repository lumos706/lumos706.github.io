#!/usr/bin/env python3
"""Restore the latest known-good Douyin evidence from repository history.

This is a local data migration, not a web refresh. It is useful when daily
non-Douyin snapshots predate the weekly retention policy and therefore no
longer contain the last successful Douyin links.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from douyin_policy import evidence_platforms, merge_douyin_snapshot
from update_travel_data import write_atomic


DEFAULT_FILES = (
    Path("src/data/travel/snapshot.json"),
    Path("src/data/travel/transport.json"),
    Path("src/data/travel/preparations.json"),
    Path("src/data/travel/reservations.json"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore retained Douyin evidence")
    parser.add_argument("--commit", required=True, help="Known-good Git commit")
    parser.add_argument("files", nargs="*", type=Path, default=DEFAULT_FILES)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def load_historical(commit: str, path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object for {path} at {commit}")
    return value


def main() -> int:
    args = parse_args()
    summaries: list[dict[str, Any]] = []
    for path in args.files:
        current = load_json(path)
        historical = load_historical(args.commit, path)
        checked_at = str(current.get("generatedAt") or historical.get("generatedAt") or "")
        metadata = merge_douyin_snapshot(
            current,
            historical,
            refresh_requested=False,
            checked_at=checked_at,
            fresh_urls=(),
        )
        current["schemaVersion"] = max(
            int(current.get("schemaVersion") or 0),
            4 if path.name == "snapshot.json" else 2,
        )
        current["activeSources"] = sorted(evidence_platforms(current))
        if path.name == "snapshot.json":
            coverage = current.get("sourceCoverage")
            if not isinstance(coverage, dict):
                coverage = {}
                current["sourceCoverage"] = coverage
            coverage["douyin"] = metadata["evidenceCount"]
            current["sourceCoverage"] = dict(sorted(coverage.items()))
        write_atomic(path.resolve(), current)
        summaries.append(
            {
                "path": path.as_posix(),
                "lastSuccessfulAt": metadata["lastSuccessfulAt"],
                "retainedEvidenceCount": metadata["retainedEvidenceCount"],
            }
        )
    print(json.dumps(summaries, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
