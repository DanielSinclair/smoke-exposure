#!/usr/bin/env python3
"""Aggregate current MTBS fire-occurrence points by ignition year."""

from __future__ import annotations

import csv
import tempfile
import zipfile
from collections import defaultdict

import shapefile

from pipeline.settings import MTBS_SOURCE, PROCESSED


def main() -> None:
    archive = MTBS_SOURCE
    totals: dict[int, dict[str, float]] = defaultdict(lambda: {"fire_count": 0, "acres_burned": 0.0})
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(temp)
        reader = shapefile.Reader(f"{temp}/S_USA.MTBS_FIRE_OCCURRENCE_PT.shp")
        fields = [field[0] for field in reader.fields[1:]]
        for raw in reader.iterRecords():
            row = dict(zip(fields, raw))
            if str(row.get("FIRE_TYPE", "")).strip().lower() != "wildfire":
                continue
            ignition_date = row.get("IG_DATE")
            if not ignition_date:
                continue
            year = ignition_date.year
            acres = float(row["ACRES"] or 0)
            totals[year]["fire_count"] += 1
            totals[year]["acres_burned"] += acres
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "mtbs_wildfires_annual.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["year", "fire_count", "acres_burned"],
            lineterminator="\n",
        )
        writer.writeheader()
        for year, values in sorted(totals.items()):
            writer.writerow({
                "year": year,
                "fire_count": int(values["fire_count"]),
                "acres_burned": round(values["acres_burned"]),
            })
    print(f"wrote {len(totals)} years to {out}")


if __name__ == "__main__":
    main()
