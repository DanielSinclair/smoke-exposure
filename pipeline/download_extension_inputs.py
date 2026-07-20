#!/usr/bin/env python3
"""Fetch official AQS PM2.5 and NOAA HMS inputs for the 2006-present screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pipeline.settings import (
    EPA_AQS_2006_2026,
    EPA_AQS_DOWNLOADS,
    NOAA_HMS_2006_2026,
    NOAA_HMS_DOWNLOADS,
    ROOT,
)


FIRST_YEAR = 2006
LAST_YEAR = 2026


def file_receipt(url: str, path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {
        "url": url,
        "local_path": str(path.relative_to(ROOT)),
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def download(url: str, path: Path, force: bool = False) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return file_receipt(url, path)
    part = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "wildfire-smoke-atlas/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, part.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    part.replace(path)
    return file_receipt(url, path)


def write_receipt(path: Path, files: list[dict[str, object]], note: str) -> None:
    previous = json.loads(path.read_text()) if path.exists() else {}
    merged = {
        str(record["local_path"]): record
        for record in previous.get("files", [])
    }
    merged.update({str(record["local_path"]): record for record in files})
    body = {
        "coverage_note": note,
        "files": [merged[key] for key in sorted(merged)],
    }
    if path.exists():
        if {key: previous.get(key) for key in body} == body:
            print(f"unchanged {path}")
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        **body,
    }, indent=2) + "\n")
    print(f"wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "years",
        nargs="*",
        type=int,
        help="calendar years; defaults to the complete 2006-2026 screen",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--hms-only", action="store_true", help="refresh HMS bundles without redownloading AQS")
    args = parser.parse_args()
    years = args.years or list(range(FIRST_YEAR, LAST_YEAR + 1))
    invalid = [year for year in years if year < FIRST_YEAR or year > LAST_YEAR]
    if invalid:
        parser.error(f"years outside {FIRST_YEAR}-{LAST_YEAR}: {invalid}")

    aqs_receipts = []
    hms_receipts = []
    for year in years:
        if not args.hms_only:
            for parameter in (88101, 88502):
                filename = f"daily_{parameter}_{year}.zip"
                url = f"https://aqs.epa.gov/aqsweb/airdata/{filename}"
                aqs_receipts.append(download(url, EPA_AQS_DOWNLOADS / filename, args.force))
        filename = f"hms_smoke{year}.zip"
        url = f"https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/Smoke_Polygons/Shapefile/Annual_Bundles/{filename}"
        hms_receipts.append(download(url, NOAA_HMS_DOWNLOADS / filename, args.force))
    if aqs_receipts:
        write_receipt(
            EPA_AQS_2006_2026 / "receipt.json",
            aqs_receipts,
            "EPA AQS daily PM2.5 annual snapshots for parameters 88101 and 88502. "
            "Files are revisionable; 2026 ends at the latest available AQS monitor date.",
        )
    write_receipt(
        NOAA_HMS_2006_2026 / "receipt.json",
        hms_receipts,
        "NOAA HMS annual smoke-polygon bundles for the complete 2006-present "
        "screen. Processing uses the earlier monitor/HMS date as each year's common cutoff.",
    )


if __name__ == "__main__":
    main()
