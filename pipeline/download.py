#!/usr/bin/env python3
"""Fetch source inputs declared in sources/manifest.json.

Large raw files are intentionally ignored by Git. Every tracked processed
artifact can be rebuilt from the URLs and checksums in the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

from pipeline.settings import MANIFEST, ROOT


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(
    url: str,
    target: Path,
    expected_sha256: str | None,
    archive_member: str | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (not expected_sha256 or sha256(target) == expected_sha256):
        print(f"ok      {target.relative_to(ROOT)}")
        return
    part = target.with_suffix(target.suffix + (".zip.part" if archive_member else ".part"))
    request = urllib.request.Request(url, headers={"User-Agent": "wildfire-smoke-atlas/1.0"})
    with urllib.request.urlopen(request) as response, part.open("wb") as output:
        shutil.copyfileobj(response, output)
    candidate = part
    if archive_member:
        extracted = target.with_suffix(target.suffix + ".extracted")
        with zipfile.ZipFile(part) as archive:
            matches = [name for name in archive.namelist() if Path(name).name == archive_member]
            if len(matches) != 1:
                raise ValueError(f"expected one {archive_member!r} in downloaded archive; found {matches}")
            with archive.open(matches[0]) as source, extracted.open("wb") as output:
                shutil.copyfileobj(source, output)
        part.unlink()
        candidate = extracted
    if expected_sha256 and sha256(candidate) != expected_sha256:
        raise ValueError(f"checksum mismatch for {target.name}")
    candidate.replace(target)
    print(f"fetched {target.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*", help="source ids; default: all downloadable inputs")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    selected = set(args.ids)
    for source in manifest["sources"]:
        target_path = source.get("local_path") or source.get("download_path")
        if not target_path or (selected and source["id"] not in selected):
            continue
        if not selected and source.get("optional_download"):
            print(f"skip    {source['id']} (optional large or access-controlled input)")
            continue
        target = ROOT / target_path
        fetch(
            source["retrieval_url"],
            target,
            source.get("sha256"),
            source.get("archive_member"),
        )


if __name__ == "__main__":
    main()
