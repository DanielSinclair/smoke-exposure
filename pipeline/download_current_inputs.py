#!/usr/bin/env python3
"""Freeze current official fire activity and provisional AirNow inputs."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pypdf import PdfReader

from pipeline.settings import (
    AIRNOW_SUPPLEMENT_END_DATE,
    AIRNOW_SUPPLEMENT_START_DATE,
    CURRENT_DATA_DATE,
    EPA_AIRNOW,
    EPA_AIRNOW_DAILY,
    ROOT,
    SOURCES,
)


USER_AGENT = "smoke-exposure/1.0 (+https://github.com/DanielSinclair/smoke-exposure)"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, path: Path) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
        path.write_bytes(body)
    return {
        "url": url,
        "local_path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def daterange(start: str, end: str):
    cursor = date.fromisoformat(start)
    final = date.fromisoformat(end)
    while cursor <= final:
        yield cursor
        cursor += timedelta(days=1)


def validate_nifc_snapshot(path: Path) -> None:
    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    display_date = date.fromisoformat(CURRENT_DATA_DATE).strftime("%B %-d, %Y")
    if display_date not in text:
        raise ValueError(f"NIFC snapshot is not dated {CURRENT_DATA_DATE}")
    if "Fires and Acres Year-to-Date" not in text or "TOTAL FIRES:" not in text:
        raise ValueError("NIFC situation report is missing required YTD fields")


def validate_ciffc_snapshot(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError("NRCan snapshot must contain exactly one national row")
    row = payload[0]
    if row.get("date") != CURRENT_DATA_DATE:
        raise ValueError(f"NRCan snapshot is not dated {CURRENT_DATA_DATE}")
    if not row.get("fire_count", {}).get("total") or not row.get("area_burned", {}).get("total"):
        raise ValueError("NRCan snapshot is missing current fire totals")


def main() -> None:
    files: list[dict[str, object]] = []

    nifc = SOURCES / "nifc" / "2026" / f"incident_management_situation_report_{CURRENT_DATA_DATE}.pdf"
    nifc_compact_date = date.fromisoformat(CURRENT_DATA_DATE).strftime("%m%d%Y")
    files.append(download(
        "https://www.nifc.gov/sites/default/files/NICC/1-Incident%20Information/IMSR/"
        f"2026/July/IMSR_CY26_{nifc_compact_date}_0.pdf",
        nifc,
    ))
    validate_nifc_snapshot(nifc)

    ciffc = SOURCES / "nrcan-cwfif" / "2026" / f"reported_fire_stats_{CURRENT_DATA_DATE}.json"
    files.append(download(
        "https://api.cwfif.nrcan.gc.ca/reported-fire-stats/ytd/by-response-type"
        f"?date={CURRENT_DATA_DATE}",
        ciffc,
    ))
    validate_ciffc_snapshot(ciffc)

    fact_sheet = EPA_AIRNOW / "docs" / "DailyDataFactSheet.pdf"
    files.append(download(
        "https://files.airnowtech.org/airnow/docs/DailyDataFactSheet.pdf",
        fact_sheet,
    ))

    airnow_files = []
    for day in daterange(AIRNOW_SUPPLEMENT_START_DATE, AIRNOW_SUPPLEMENT_END_DATE):
        compact = day.strftime("%Y%m%d")
        url = f"https://files.airnowtech.org/airnow/2026/{compact}/daily_data_v2.dat"
        record = download(url, EPA_AIRNOW_DAILY / f"{day.isoformat()}.dat")
        airnow_files.append(record)

    receipt = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "publication_cutoff": CURRENT_DATA_DATE,
        "airnow_complete_day_cutoff": AIRNOW_SUPPLEMENT_END_DATE,
        "coverage_note": (
            "NIFC and NRCan CWFIF are provisional YTD snapshots. AirNow PM2.5-24hr "
            "files supplement lagged AQS after 2026-05-31 and remain preliminary."
        ),
        "files": files,
        "airnow_daily_files": airnow_files,
    }
    receipt_path = SOURCES / "current-2026-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {receipt_path} with {len(airnow_files)} AirNow daily snapshots")


if __name__ == "__main__":
    main()
