#!/usr/bin/env python3
"""Aggregate comprehensive U.S. and Canadian reported-fire occurrence archives.

FPA FOD and NFDB are retained as separate source-covered series because their
reporting systems, coverage, and deduplication rules differ. The derived files
are deliberately compact: annual source rollups and a fixed spatial grid for
the site. Raw multi-million-row archives remain provider-owned download caches.
"""

from __future__ import annotations

from collections import defaultdict
import csv
import io
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from pipeline.settings import PROCESSED, SOURCES


FPA_ARCHIVE = SOURCES / "usfs-fpa-fod" / "2022" / "RDS-2013-0009.6_Data_Format4_SQLITE.zip"
NFDB_ARCHIVE = SOURCES / "nrcan-nfdb" / "2026-06-08" / "NFDB_point_txt.zip"
ACRES_PER_HECTARE = 2.4710538147
GRID_COLUMNS = 30
GRID_ROWS = 24


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def grid_cell(latitude: float, longitude: float) -> tuple[int, int] | None:
    if not 24 <= latitude <= 84 or not -170 <= longitude <= -50:
        return None
    x = min(GRID_COLUMNS - 1, max(0, int((longitude + 170) // 4)))
    y = min(GRID_ROWS - 1, max(0, int((84 - latitude) // 2.5)))
    return x, y


def aggregate_record(
    annual: dict[tuple[str, int], dict[str, object]],
    tiles: dict[tuple[int, int], dict[str, object]],
    *,
    geography: str,
    year: int,
    acres: float,
    latitude: float | None,
    longitude: float | None,
    region: str,
    source_id: str,
) -> None:
    annual_group = annual.setdefault((geography, year), {
        "geography": geography,
        "year": year,
        "fire_count": 0,
        "burned_acres": 0.0,
        "records_with_coordinates": 0,
        "source_id": source_id,
    })
    annual_group["fire_count"] = int(annual_group["fire_count"]) + 1
    annual_group["burned_acres"] = float(annual_group["burned_acres"]) + max(0, acres)
    if latitude is None or longitude is None:
        return
    cell = grid_cell(latitude, longitude)
    if cell is None:
        return
    annual_group["records_with_coordinates"] = int(annual_group["records_with_coordinates"]) + 1
    if not 1992 <= year <= 2020:
        return
    tile = tiles.setdefault(cell, {
        "x": cell[0],
        "y": cell[1],
        "year_start": 1992,
        "year_end": 2020,
        "fire_count": 0,
        "burned_acres": 0.0,
        "us_fire_count": 0,
        "canada_fire_count": 0,
        "regions": set(),
        "source_ids": set(),
    })
    tile["fire_count"] = int(tile["fire_count"]) + 1
    tile["burned_acres"] = float(tile["burned_acres"]) + max(0, acres)
    country_key = "us_fire_count" if geography == "United States" else "canada_fire_count"
    tile[country_key] = int(tile[country_key]) + 1
    if region:
        tile["regions"].add(region)
    tile["source_ids"].add(source_id)


def load_fpa(
    annual: dict[tuple[str, int], dict[str, object]],
    tiles: dict[tuple[int, int], dict[str, object]],
) -> None:
    with zipfile.ZipFile(FPA_ARCHIVE) as archive, tempfile.TemporaryDirectory() as temp:
        member = next(name for name in archive.namelist() if name.endswith(".sqlite"))
        archive.extract(member, temp)
        database = Path(temp) / member
        connection = sqlite3.connect(database)
        try:
            cursor = connection.execute(
                "SELECT FIRE_YEAR, FIRE_SIZE, LATITUDE, LONGITUDE, STATE FROM Fires"
            )
            for year, acres, latitude, longitude, state in cursor:
                if year is None or not 1992 <= int(year) <= 2020:
                    continue
                aggregate_record(
                    annual,
                    tiles,
                    geography="United States",
                    year=int(year),
                    acres=float(acres or 0),
                    latitude=float(latitude) if latitude is not None else None,
                    longitude=float(longitude) if longitude is not None else None,
                    region=str(state or "").strip(),
                    source_id="usfs-fpa-fod-1992-2020",
                )
        finally:
            connection.close()


def load_nfdb(
    annual: dict[tuple[str, int], dict[str, object]],
    tiles: dict[tuple[int, int], dict[str, object]],
) -> None:
    with zipfile.ZipFile(NFDB_ARCHIVE) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".txt"))
        with archive.open(member) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            for row in reader:
                prescribed = str(row.get("PRESCRIBED", "")).strip().lower()
                fire_type = str(row.get("FIRE_TYPE", "")).strip().lower()
                if prescribed in {"1", "true", "yes", "y"} or "prescribed" in fire_type:
                    continue
                try:
                    year = int(row["YEAR"])
                    acres = float(row.get("SIZE_HA") or 0) * ACRES_PER_HECTARE
                except (KeyError, TypeError, ValueError):
                    continue
                if not 1950 <= year <= 2025:
                    continue
                try:
                    latitude = float(row["LATITUDE"])
                    longitude = float(row["LONGITUDE"])
                except (KeyError, TypeError, ValueError):
                    latitude = longitude = None
                aggregate_record(
                    annual,
                    tiles,
                    geography="Canada",
                    year=year,
                    acres=acres,
                    latitude=latitude,
                    longitude=longitude,
                    region=str(row.get("SRC_AGENCY") or "").strip(),
                    source_id="nrcan-nfdb-all-fire-points-2026-06-08",
                )


def main() -> None:
    annual: dict[tuple[str, int], dict[str, object]] = {}
    tiles: dict[tuple[int, int], dict[str, object]] = {}
    load_fpa(annual, tiles)
    load_nfdb(annual, tiles)

    annual_rows = []
    for (geography, year), group in sorted(annual.items(), key=lambda item: (item[0][1], item[0][0])):
        annual_rows.append({
            **group,
            "burned_acres": round(float(group["burned_acres"])),
            "coverage_status": (
                "deduplicated_source_release" if geography == "United States"
                else "agency_year_coverage_varies"
            ),
            "comparable_to_other_geography": "false",
        })

    tile_rows = []
    for group in sorted(tiles.values(), key=lambda row: (int(row["y"]), int(row["x"]))):
        regions = sorted(group.pop("regions"))
        tile_rows.append({
            **group,
            "burned_acres": round(float(group["burned_acres"])),
            "regions": "; ".join(regions),
            "source_ids": ";".join(sorted(group["source_ids"])),
            "coverage_note": "FPA FOD and NFDB are source-covered but not cross-country comparable",
        })

    write_csv(
        PROCESSED / "all_fire_incidents_annual_source_covered.csv",
        annual_rows,
        [
            "geography", "year", "fire_count", "burned_acres", "records_with_coordinates",
            "source_id", "coverage_status", "comparable_to_other_geography",
        ],
    )
    write_csv(
        PROCESSED / "all_fire_density_tiles_1992_2020.csv",
        tile_rows,
        [
            "x", "y", "year_start", "year_end", "fire_count", "burned_acres",
            "us_fire_count", "canada_fire_count", "regions", "source_ids", "coverage_note",
        ],
    )
    print(
        f"wrote {len(annual_rows):,} country-year all-fire rollups and "
        f"{len(tile_rows):,} spatial tiles"
    )


if __name__ == "__main__":
    main()
