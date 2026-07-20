#!/usr/bin/env python3
"""Build a source-covered monthly North American wildfire incident catalog.

This is an incident-record history, not a smoke-exposure reconstruction. Each
country-year uses one designated source lane to avoid double counting overlapping
archives. Missing coverage is emitted explicitly with blank metrics, never zero.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
import gzip
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from pipeline.settings import (
    MTBS_SOURCE,
    NIFC_INFORM_RECORDS,
    NIFC_INFORM_SNAPSHOT_DATE,
    PROCESSED,
    SOURCES,
)


FPA_ARCHIVE = SOURCES / "usfs-fpa-fod" / "2022" / "RDS-2013-0009.6_Data_Format4_SQLITE.zip"
NFDB_ARCHIVE = SOURCES / "nrcan-nfdb" / "2026-06-08" / "NFDB_point_txt.zip"
ACRES_PER_HECTARE = 2.4710538147
FIRST_YEAR = 1950
LAST_YEAR = 2026

SOURCE_LANES = [
    {
        "source_id": "nrcan-nfdb-all-fire-points-2026-06-08",
        "geography": "Canada", "year_start": 1950, "year_end": 2025,
        "scope": "provincial and territorial reported fire point records",
        "coverage_tier": "all_reported_occurrences",
        "coverage_status": "agency_year_coverage_varies",
        "source_url": "https://cwfis.cfs.nrcan.gc.ca/ha/nfdb",
        "raw_record_url": "https://cwfis.cfs.nrcan.gc.ca/downloads/nfdb/fire_pnt/current_version/NFDB_point_txt.zip",
    },
    {
        "source_id": "mtbs-fire-occurrence",
        "geography": "United States", "year_start": 1984, "year_end": 1991,
        "scope": "mapped wildfires at least 500 acres in the East or 1,000 acres in the West",
        "coverage_tier": "large_fires_only",
        "coverage_status": "complete_release_year",
        "source_url": "https://www.mtbs.gov/",
        "raw_record_url": "https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.MTBS_FIRE_OCCURRENCE_PT.zip",
    },
    {
        "source_id": "usfs-fpa-fod-1992-2020",
        "geography": "United States", "year_start": 1992, "year_end": 2020,
        "scope": "deduplicated final reported wildfire occurrences",
        "coverage_tier": "all_reported_occurrences",
        "coverage_status": "deduplicated_source_release",
        "source_url": "https://doi.org/10.2737/RDS-2013-0009.6",
        "raw_record_url": "https://www.fs.usda.gov/rds/archive/products/RDS-2013-0009.6/RDS-2013-0009.6_Data_Format4_SQLITE.zip",
    },
    {
        "source_id": "nifc-inform-fodr-2021-present",
        "geography": "United States", "year_start": 2021, "year_end": 2026,
        "scope": "public InFORM wildfire occurrence records, approved and unapproved",
        "coverage_tier": "live_occurrence_records",
        "coverage_status": "live_snapshot_revisionable",
        "source_url": "https://www.arcgis.com/home/item.html?id=60a94840152b4a89bec467a9f052f135",
        "raw_record_url": "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/InFORM_FireOccurrence_Public/FeatureServer/0",
    },
]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def empty_group() -> dict[str, object]:
    return {
        "record_count": 0,
        "burned_acres": 0.0,
        "named_record_count": 0,
        "records_with_coordinates": 0,
        "certified_or_final_count": 0,
    }


def add_record(
    groups: dict[tuple[str, int, int, str], dict[str, object]],
    annual_unknown_month: dict[tuple[str, int, str], dict[str, object]],
    *,
    geography: str,
    year: int,
    month: int | None,
    source_id: str,
    acres: float,
    name: str,
    latitude: float | None,
    longitude: float | None,
    certified_or_final: bool,
) -> None:
    if not FIRST_YEAR <= year <= LAST_YEAR:
        return
    if month is None or not 1 <= month <= 12:
        group = annual_unknown_month.setdefault((geography, year, source_id), empty_group())
    else:
        group = groups.setdefault((geography, year, month, source_id), empty_group())
    group["record_count"] = int(group["record_count"]) + 1
    group["burned_acres"] = float(group["burned_acres"]) + max(0, acres)
    group["named_record_count"] = int(group["named_record_count"]) + int(bool(name.strip()))
    group["records_with_coordinates"] = int(group["records_with_coordinates"]) + int(
        latitude is not None and longitude is not None
    )
    group["certified_or_final_count"] = int(group["certified_or_final_count"]) + int(certified_or_final)


def parse_month(value: object) -> int | None:
    try:
        month = int(value)
    except (TypeError, ValueError):
        return None
    return month if 1 <= month <= 12 else None


def load_canada_all_1950_2025(groups, annual_unknown_month) -> None:
    with zipfile.ZipFile(NFDB_ARCHIVE) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".txt"))
        with archive.open(member) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            for row in reader:
                try:
                    year = int(row["YEAR"])
                except (KeyError, TypeError, ValueError):
                    continue
                if not 1950 <= year <= 2025:
                    continue
                if "prescribed" in str(row.get("FIRE_TYPE", "")).lower() or str(row.get("PRESCRIBED", "")).strip().lower() in {"1", "true", "yes", "y"}:
                    continue
                add_record(
                    groups, annual_unknown_month,
                    geography="Canada", year=year, month=parse_month(row.get("MONTH")),
                    source_id="nrcan-nfdb-all-fire-points-2026-06-08",
                    acres=float(row.get("SIZE_HA") or 0) * ACRES_PER_HECTARE,
                    name=str(row.get("FIRENAME") or "").strip(),
                    latitude=float(row["LATITUDE"]) if row.get("LATITUDE") else None,
                    longitude=float(row["LONGITUDE"]) if row.get("LONGITUDE") else None,
                    certified_or_final=True,
                )


def load_us_mtbs_1984_1991(groups, annual_unknown_month) -> None:
    import shapefile

    with zipfile.ZipFile(MTBS_SOURCE) as archive, tempfile.TemporaryDirectory() as temp:
        archive.extractall(temp)
        shp_path = next(Path(temp).glob("*.shp"))
        reader = shapefile.Reader(str(shp_path))
        fields = [field[0] for field in reader.fields[1:]]
        for raw in reader.iterRecords():
            row = dict(zip(fields, raw))
            if str(row.get("FIRE_TYPE", "")).strip().lower() != "wildfire":
                continue
            ignition = row.get("IG_DATE")
            if not ignition or not 1984 <= ignition.year <= 1991:
                continue
            add_record(
                groups, annual_unknown_month,
                geography="United States", year=ignition.year, month=ignition.month,
                source_id="mtbs-fire-occurrence", acres=float(row.get("ACRES") or 0),
                name=str(row.get("FIRE_NAME") or "").strip(),
                latitude=float(row["LATITUDE"]) if row.get("LATITUDE") is not None else None,
                longitude=float(row["LONGITUDE"]) if row.get("LONGITUDE") is not None else None,
                certified_or_final=True,
            )


def load_us_fpa_1992_2020(groups, annual_unknown_month) -> None:
    with zipfile.ZipFile(FPA_ARCHIVE) as archive, tempfile.TemporaryDirectory() as temp:
        member = next(name for name in archive.namelist() if name.endswith(".sqlite"))
        archive.extract(member, temp)
        connection = sqlite3.connect(Path(temp) / member)
        try:
            cursor = connection.execute(
                "SELECT FIRE_YEAR, DISCOVERY_DATE, FIRE_SIZE, FIRE_NAME, LATITUDE, LONGITUDE "
                "FROM Fires WHERE FIRE_YEAR BETWEEN 1992 AND 2020"
            )
            for year, discovery_date, acres, name, latitude, longitude in cursor:
                try:
                    month = datetime.strptime(discovery_date, "%m/%d/%Y").month
                except (TypeError, ValueError):
                    month = None
                add_record(
                    groups, annual_unknown_month,
                    geography="United States", year=int(year), month=month,
                    source_id="usfs-fpa-fod-1992-2020", acres=float(acres or 0),
                    name=str(name or "").strip(),
                    latitude=float(latitude) if latitude is not None else None,
                    longitude=float(longitude) if longitude is not None else None,
                    certified_or_final=True,
                )
        finally:
            connection.close()


def inform_month(milliseconds: object) -> int | None:
    try:
        return datetime.fromtimestamp(float(milliseconds) / 1000, timezone.utc).month
    except (TypeError, ValueError, OSError):
        return None


def first_numeric(*values: object) -> float:
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number >= 0:
            return number
    return 0.0


def load_us_inform_2021_2026(groups, annual_unknown_month) -> None:
    if not NIFC_INFORM_RECORDS.exists():
        raise FileNotFoundError(
            f"missing {NIFC_INFORM_RECORDS}; run pipeline.download_fire_history_inputs"
        )
    with gzip.open(NIFC_INFORM_RECORDS, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            year = int(row["CalendarYear"])
            add_record(
                groups, annual_unknown_month,
                geography="United States", year=year,
                month=inform_month(row.get("FireDiscoveryDateTime")),
                source_id="nifc-inform-fodr-2021-present",
                acres=first_numeric(row.get("FinalAcres"), row.get("CalculatedAcres"), row.get("IncidentSize")),
                name=str(row.get("IncidentName") or "").strip(),
                latitude=float(row["InitialLatitude"]) if row.get("InitialLatitude") is not None else None,
                longitude=float(row["InitialLongitude"]) if row.get("InitialLongitude") is not None else None,
                certified_or_final=(
                    str(row.get("ADSPermissionState") or "").upper() == "CERTIFIED"
                    or row.get("FinalFireReportApprovedDate") is not None
                ),
            )


def lane_for(geography: str, year: int) -> dict[str, object] | None:
    for lane in SOURCE_LANES:
        if lane["geography"] == geography and int(lane["year_start"]) <= year <= int(lane["year_end"]):
            return lane
    return None


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    groups: dict[tuple[str, int, int, str], dict[str, object]] = {}
    unknown_month: dict[tuple[str, int, str], dict[str, object]] = {}
    load_canada_all_1950_2025(groups, unknown_month)
    load_us_mtbs_1984_1991(groups, unknown_month)
    load_us_fpa_1992_2020(groups, unknown_month)
    load_us_inform_2021_2026(groups, unknown_month)

    snapshot = date.fromisoformat(NIFC_INFORM_SNAPSHOT_DATE)
    monthly_rows: list[dict[str, object]] = []
    annual_groups: dict[tuple[str, int], dict[str, object]] = {}
    for geography in ("United States", "Canada"):
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            lane = lane_for(geography, year)
            for month in range(1, 13):
                group = groups.get((geography, year, month, str(lane["source_id"]))) if lane else None
                future = year == snapshot.year and month > snapshot.month
                current_partial = year == snapshot.year and month == snapshot.month
                coverage_status = (
                    "not_yet_observed" if future else
                    "no_national_incident_catalog" if lane is None else
                    str(lane["coverage_status"])
                )
                row = {
                    "year": year,
                    "month": month,
                    "geography": geography,
                    "record_count": "" if lane is None or future else int((group or empty_group())["record_count"]),
                    "burned_acres": "" if lane is None or future else round(float((group or empty_group())["burned_acres"])),
                    "named_record_count": "" if lane is None or future else int((group or empty_group())["named_record_count"]),
                    "records_with_coordinates": "" if lane is None or future else int((group or empty_group())["records_with_coordinates"]),
                    "certified_or_final_count": "" if lane is None or future else int((group or empty_group())["certified_or_final_count"]),
                    "source_id": "" if lane is None else lane["source_id"],
                    "source_scope": "" if lane is None else lane["scope"],
                    "coverage_tier": "none" if lane is None else lane["coverage_tier"],
                    "coverage_status": coverage_status,
                    "calendar_window_complete": str(lane is not None and not current_partial and not future).lower(),
                    "provisional": str(year == 2026).lower(),
                    "comparable_over_time": "false",
                    "causal_smoke_attribution": "false",
                }
                monthly_rows.append(row)
                if row["record_count"] == "":
                    continue
                annual = annual_groups.setdefault((geography, year), {
                    "record_count": 0, "burned_acres": 0, "named_record_count": 0,
                    "records_with_coordinates": 0, "certified_or_final_count": 0,
                })
                for field in annual:
                    annual[field] = int(annual[field]) + int(row[field])

    annual_rows = []
    for geography in ("United States", "Canada"):
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            lane = lane_for(geography, year)
            values = annual_groups.get((geography, year))
            unknown_values = (
                unknown_month.get((geography, year, str(lane["source_id"])), empty_group())
                if lane else empty_group()
            )
            totals = {
                field: int((values or empty_group())[field]) + int(unknown_values[field])
                for field in empty_group()
            } if values is not None else None
            annual_rows.append({
                "year": year,
                "geography": geography,
                "record_count": "" if totals is None else totals["record_count"],
                "burned_acres": "" if totals is None else totals["burned_acres"],
                "named_record_count": "" if totals is None else totals["named_record_count"],
                "records_with_coordinates": "" if totals is None else totals["records_with_coordinates"],
                "certified_or_final_count": "" if totals is None else totals["certified_or_final_count"],
                "records_with_unknown_month": 0 if lane is None else unknown_values["record_count"],
                "source_id": "" if lane is None else lane["source_id"],
                "source_scope": "" if lane is None else lane["scope"],
                "coverage_tier": "none" if lane is None else lane["coverage_tier"],
                "coverage_status": "no_national_incident_catalog" if lane is None else lane["coverage_status"],
                "provisional": str(year == 2026).lower(),
                "comparable_over_time": "false",
                "causal_smoke_attribution": "false",
            })

    source_rows = [{
        **lane,
        "raw_records_in_repository": "false",
        "derived_monthly_output": "data/processed/fire_incidents_monthly_source_covered.csv",
        "deduplication_rule": "one designated source lane per geography-year; no overlapping source union",
        "trend_safe": "false",
    } for lane in SOURCE_LANES]

    monthly_fields = [
        "year", "month", "geography", "record_count", "burned_acres",
        "named_record_count", "records_with_coordinates", "certified_or_final_count",
        "source_id", "source_scope", "coverage_tier", "coverage_status",
        "calendar_window_complete", "provisional", "comparable_over_time",
        "causal_smoke_attribution",
    ]
    annual_fields = [
        "year", "geography", "record_count", "burned_acres", "named_record_count",
        "records_with_coordinates", "certified_or_final_count", "records_with_unknown_month",
        "source_id", "source_scope", "coverage_tier", "coverage_status", "provisional",
        "comparable_over_time", "causal_smoke_attribution",
    ]
    source_fields = [
        "source_id", "geography", "year_start", "year_end", "scope", "coverage_tier",
        "coverage_status", "source_url", "raw_record_url", "raw_records_in_repository",
        "derived_monthly_output", "deduplication_rule", "trend_safe",
    ]
    write_csv(PROCESSED / "fire_incidents_monthly_source_covered.csv", monthly_rows, monthly_fields)
    write_csv(PROCESSED / "fire_incidents_annual_catalog_1950_2026.csv", annual_rows, annual_fields)
    write_csv(PROCESSED / "fire_incident_catalog_sources.csv", source_rows, source_fields)
    print(
        f"wrote {len(monthly_rows):,} monthly coverage rows, {len(annual_rows):,} annual rows, "
        f"and {len(source_rows):,} source-lane records; U.S. snapshot {NIFC_INFORM_SNAPSHOT_DATE}"
    )


if __name__ == "__main__":
    main()
