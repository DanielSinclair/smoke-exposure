#!/usr/bin/env python3
"""Freeze NOAA Storm Events details used to screen historical smoke evidence.

Storm Events is a corroborating fire-incident source, not a smoke-exposure
archive. Event types change over time and narratives are not a systematic smoke
observation network. The downloader records the current official annual files
and exact bytes/checksums so the candidate screen is reproducible.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

from pipeline.settings import NOAA_STORM_EVENTS_1950_2005, NOAA_STORM_EVENTS_DOWNLOADS, ROOT


INDEX_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
USER_AGENT = "smoke-exposure/1.0 (+https://github.com/DanielSinclair/smoke-exposure)"
DETAIL_RE = re.compile(r"StormEvents_details-ftp_v1\.0_d(\d{4})_c(\d{8})\.csv\.gz$")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def request(url: str):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=120
    )


def latest_detail_files() -> dict[int, tuple[str, str]]:
    with request(INDEX_URL) as response:
        index = response.read().decode("utf-8", "replace")
    parser = LinkParser()
    parser.feed(index)
    output: dict[int, tuple[str, str]] = {}
    for href in parser.hrefs:
        match = DETAIL_RE.search(href)
        if not match:
            continue
        year, created = int(match.group(1)), match.group(2)
        if 1950 <= year <= 2005 and (year not in output or created > output[year][1]):
            output[year] = (href, created)
    if sorted(output) != list(range(1950, 2006)):
        raise ValueError("NOAA index did not expose one detail file for every 1950–2005 year")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    NOAA_STORM_EVENTS_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    files = []
    for year, (name, created) in sorted(latest_detail_files().items()):
        path = NOAA_STORM_EVENTS_DOWNLOADS / name
        if args.force or not path.exists():
            partial = path.with_suffix(path.suffix + ".part")
            with request(INDEX_URL + name) as response, partial.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            partial.replace(path)
        files.append({
            "year": year,
            "source_revision": created,
            "source_url": INDEX_URL + name,
            "local_path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    receipt = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_index": INDEX_URL,
        "coverage": "1950-2005 annual detail files",
        "coverage_warning": (
            "Storm Events event-type coverage changes over time. Wildfire records are "
            "incident corroboration only; narratives are not a complete smoke archive."
        ),
        "files": files,
    }
    NOAA_STORM_EVENTS_1950_2005.mkdir(parents=True, exist_ok=True)
    receipt_path = NOAA_STORM_EVENTS_1950_2005 / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {receipt_path} for {len(files)} official annual files")


if __name__ == "__main__":
    main()
