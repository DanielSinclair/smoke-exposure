#!/usr/bin/env python3
"""Build a two-row provisional 2026 YTD fire-activity table."""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_UP
import json
import re

from pypdf import PdfReader

from pipeline.settings import CURRENT_DATA_DATE, PROCESSED, SOURCES


ACRES_PER_HECTARE = Decimal("2.471053814671653")


def parse_nifc() -> tuple[int, int, str]:
    path = SOURCES / "nifc" / "2026" / f"incident_management_situation_report_{CURRENT_DATA_DATE}.pdf"
    text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    ytd = text.split("Fires and Acres Year-to-Date", maxsplit=1)[-1]
    fires_match = re.search(r"TOTAL FIRES:\s+(?:[\d,]+\s+){6}([\d,]+)", ytd)
    acres_match = re.search(r"TOTAL ACRES:\s+(?:[\d,]+\s+){6}([\d,]+)", ytd)
    if not fires_match or not acres_match:
        raise ValueError("Could not parse NIFC IMSR YTD statistics")
    return (
        int(fires_match.group(1).replace(",", "")),
        int(acres_match.group(1).replace(",", "")),
        CURRENT_DATA_DATE,
    )


def parse_ciffc() -> tuple[int, Decimal, str]:
    path = SOURCES / "nrcan-cwfif" / "2026" / f"reported_fire_stats_{CURRENT_DATA_DATE}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))[0]
    return (
        int(payload["fire_count"]["total"]),
        Decimal(str(payload["area_burned"]["total"])),
        payload["date"],
    )


def main() -> None:
    us_fires, us_acres, us_timestamp = parse_nifc()
    ca_fires, ca_hectares, ca_date = parse_ciffc()
    ca_acres = (ca_hectares * ACRES_PER_HECTARE).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    rows = [
        {
            "year": 2026,
            "geography": "United States",
            "fire_count": us_fires,
            "burned_area_ha": "",
            "burned_area_acres": us_acres,
            "as_of_date": CURRENT_DATA_DATE,
            "source_timestamp": us_timestamp,
            "source_dataset": "NIFC Incident Management Situation Report",
            "source_url": "https://www.nifc.gov/nicc/incident-information/imsr",
            "status": "year_to_date_preliminary_revisionable",
            "complete": "false",
            "comparable_to_historical_complete_series": "false",
        },
        {
            "year": 2026,
            "geography": "Canada",
            "fire_count": ca_fires,
            "burned_area_ha": format(ca_hectares, "f"),
            "burned_area_acres": ca_acres,
            "as_of_date": ca_date,
            "source_timestamp": ca_date,
            "source_dataset": "NRCan Canadian Wildland Fire Information Framework",
            "source_url": (
                "https://api.cwfif.nrcan.gc.ca/reported-fire-stats/ytd/"
                f"by-response-type?date={CURRENT_DATA_DATE}"
            ),
            "status": "year_to_date_preliminary_revisionable",
            "complete": "false",
            "comparable_to_historical_complete_series": "false",
        },
    ]
    output = PROCESSED / "current_fire_activity_2026.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
