#!/usr/bin/env python3
"""Write a tracked SHA-256 inventory for every processed artifact."""

from __future__ import annotations

import hashlib
import json

from pipeline.settings import PROCESSED, PROCESSED_CHECKSUMS, ROOT


OUTPUT = PROCESSED_CHECKSUMS


def sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    artifacts = []
    for path in sorted(PROCESSED.rglob("*")):
        if not path.is_file():
            continue
        artifacts.append({
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    payload = {
        "algorithm": "sha256",
        "generated_at": "2026-07-18T20:00:00Z",
        "artifacts": artifacts,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote checksums for {len(artifacts)} processed artifacts")


if __name__ == "__main__":
    main()
