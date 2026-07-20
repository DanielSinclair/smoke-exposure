#!/usr/bin/env python3
"""Build the 2006-2026 EPA monitor + NOAA HMS smoke-coincidence screen.

This product is deliberately not a continuation of Stanford wildfire-
attributable PM2.5. A qualifying site-day has observed total PM2.5 at or above
35.5 ug/m3 and a monitor point inside an HMS smoke polygon. County population
is attached once per qualifying county-day as an indicative spatial scale; it
does not claim that every county resident was exposed.

The annual AQS files contain alternate exceptional-event summaries. We retain
"Included" rows and ignore "Excluded" variants so smoke days are not
silently removed. The bulk daily files do not expose the underlying RF/RT/RM
fire qualifier codes; HMS coincidence is therefore the only fire/smoke screen.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import io
import json
import math
from pathlib import Path
import statistics
import tempfile
import zipfile

import shapefile

from pipeline.settings import (
    AIRNOW_SUPPLEMENT_END_DATE,
    AIRNOW_SUPPLEMENT_START_DATE,
    CENSUS_2020,
    EPA_AIRNOW_DAILY,
    EPA_AQS_DOWNLOADS,
    NOAA_HMS_DOWNLOADS,
    PROCESSED,
)


FIRST_YEAR = 2006
LAST_YEAR = 2026
YEARS = tuple(range(FIRST_YEAR, LAST_YEAR + 1))
FULL_YEAR_END = 2025
PARAMETERS = (88101, 88502)
PM25_THRESHOLD = 35.5
MIN_OBSERVATION_PERCENT = 75.0
BROAD_POPULATION = 10_000_000
SAME_CUTOFF_MONTH_DAY = (7, 18)
MODEL_ID = "AQS_HMS_MONITOR_COINCIDENCE_V3"
COMPOSITE_MODEL_ID = "AQS_AIRNOW_HMS_MONITOR_COINCIDENCE_V3"
EXCLUDED_STATE_FIPS = {"02", "15"}
INCLUDED_EVENT_TYPES = {"none", "no events", "included", "events included"}
EVENT_INCLUDED_TYPES = {"included", "events included"}
BALANCED_PANEL_YEARS = tuple(range(FIRST_YEAR, FULL_YEAR_END + 1))
BALANCED_PANEL_MIN_COVERAGE = 0.75


@dataclass(frozen=True)
class AqsLoadAudit:
    data_through: str
    raw_rows: int
    selected_site_days: int
    event_included_rows: int
    event_excluded_rows_ignored: int
    event_excluded_only_site_days: int
    invalid_or_incomplete_rows_ignored: int


def load_county_population() -> dict[str, int]:
    populations: dict[str, int] = {}
    source = CENSUS_2020 / "co-est2020-alldata.csv"
    with source.open(newline="", encoding="latin-1") as handle:
        for row in csv.DictReader(handle):
            if row["SUMLEV"] != "050":
                continue
            state = row["STATE"].zfill(2)
            if state in EXCLUDED_STATE_FIPS or int(state) > 56:
                continue
            populations[state + row["COUNTY"].zfill(3)] = int(row["POPESTIMATE2020"])
    return populations


def _event_type(raw: str) -> str:
    return " ".join(raw.strip().lower().split()) or "none"


def load_aqs_year(
    year: int,
    download_dir: Path = EPA_AQS_DOWNLOADS,
) -> tuple[dict[tuple[str, str], dict[str, object]], AqsLoadAudit]:
    """Return one maximum valid daily observation per physical AQS site-day.

    AQS daily files repeat summaries by pollutant standard, POC and exceptional-
    event treatment. We keep only summaries with events included (or with no
    event) and then take the maximum valid daily mean across PM2.5 instruments
    at a physical site. This preserves high observations without double-counting
    duplicated regulatory-standard rows.
    """

    monitor_days: dict[tuple[str, str], dict[str, object]] = {}
    data_through = ""
    raw_rows = 0
    event_included_rows = 0
    event_excluded_rows_ignored = 0
    event_excluded_site_days: set[tuple[str, str]] = set()
    invalid_or_incomplete_rows_ignored = 0
    for parameter in PARAMETERS:
        path = download_dir / f"daily_{parameter}_{year}.zip"
        if not path.exists():
            raise FileNotFoundError(
                f"missing {path}; run python -m pipeline.download_extension_inputs {year}"
            )
        with zipfile.ZipFile(path) as archive:
            member = next(name for name in archive.namelist() if name.endswith(".csv"))
            with archive.open(member) as binary:
                reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
                for row in reader:
                    raw_rows += 1
                    day = row["Date Local"]
                    data_through = max(data_through, day)
                    state = row["State Code"].zfill(2)
                    if state in EXCLUDED_STATE_FIPS or not state.isdigit() or int(state) > 56:
                        continue
                    event_type = _event_type(row.get("Event Type", ""))
                    if event_type not in INCLUDED_EVENT_TYPES:
                        event_excluded_rows_ignored += 1
                        site = state + row["County Code"].zfill(3) + row["Site Num"].zfill(4)
                        event_excluded_site_days.add((day, site))
                        continue
                    try:
                        observation_percent = float(row["Observation Percent"])
                        pm25 = float(row["Arithmetic Mean"])
                        latitude = float(row["Latitude"])
                        longitude = float(row["Longitude"])
                    except (TypeError, ValueError):
                        invalid_or_incomplete_rows_ignored += 1
                        continue
                    if observation_percent < MIN_OBSERVATION_PERCENT or not math.isfinite(pm25) or pm25 < 0:
                        invalid_or_incomplete_rows_ignored += 1
                        continue
                    site = state + row["County Code"].zfill(3) + row["Site Num"].zfill(4)
                    key = (day, site)
                    included = event_type in EVENT_INCLUDED_TYPES
                    if included:
                        event_included_rows += 1
                    candidate = {
                        "county": state + row["County Code"].zfill(3),
                        "latitude": latitude,
                        "longitude": longitude,
                        "pm25": pm25,
                        "parameter_code": parameter,
                        "event_included": included,
                    }
                    previous = monitor_days.get(key)
                    if previous is None or pm25 > float(previous["pm25"]):
                        monitor_days[key] = candidate
                    elif pm25 == float(previous["pm25"]) and included:
                        previous["event_included"] = True
    return monitor_days, AqsLoadAudit(
        data_through=data_through,
        raw_rows=raw_rows,
        selected_site_days=len(monitor_days),
        event_included_rows=event_included_rows,
        event_excluded_rows_ignored=event_excluded_rows_ignored,
        event_excluded_only_site_days=len(event_excluded_site_days.difference(monitor_days)),
        invalid_or_incomplete_rows_ignored=invalid_or_incomplete_rows_ignored,
    )


def load_airnow_supplement() -> tuple[dict[tuple[str, str], dict[str, object]], str]:
    """Return preliminary AirNow PM2.5-24hr site-days after the AQS cutoff."""

    monitor_days: dict[tuple[str, str], dict[str, object]] = {}
    cursor = date.fromisoformat(AIRNOW_SUPPLEMENT_START_DATE)
    end = date.fromisoformat(AIRNOW_SUPPLEMENT_END_DATE)
    while cursor <= end:
        day = cursor.isoformat()
        path = EPA_AIRNOW_DAILY / f"{day}.dat"
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.reader(handle, delimiter="|"):
                if len(row) < 13 or row[3].upper() != "PM2.5-24HR":
                    continue
                if row[4].upper() != "UG/M3" or row[6] != "24":
                    continue
                full_aqsid = row[12].strip()
                aqsid = row[1].strip().zfill(9)
                if not full_aqsid.startswith("840") or len(aqsid) != 9:
                    continue
                state = aqsid[:2]
                if state in EXCLUDED_STATE_FIPS or not state.isdigit() or int(state) > 56:
                    continue
                try:
                    pm25 = float(row[5])
                    latitude = float(row[10])
                    longitude = float(row[11])
                except (TypeError, ValueError):
                    continue
                if pm25 < 0:
                    continue
                key = (day, aqsid)
                candidate = {
                    "county": aqsid[:5],
                    "latitude": latitude,
                    "longitude": longitude,
                    "pm25": pm25,
                    "parameter_code": "AIRNOW_PM25_24HR",
                    "event_included": False,
                }
                previous = monitor_days.get(key)
                if previous is None or pm25 > float(previous["pm25"]):
                    monitor_days[key] = candidate
        cursor += timedelta(days=1)
    return monitor_days, AIRNOW_SUPPLEMENT_END_DATE


def parse_hms_datetime(raw: str) -> datetime:
    return datetime.strptime(raw.strip()[:12], "%Y%j %H%M")


def ring_contains(point_x: float, point_y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > point_y) != (y2 > point_y):
            crossing_x = (x2 - x1) * (point_y - y1) / (y2 - y1) + x1
            if point_x < crossing_x:
                inside = not inside
        previous = current
    return inside


def shape_contains(shape: shapefile.Shape, longitude: float, latitude: float) -> bool:
    xmin, ymin, xmax, ymax = shape.bbox
    if not (xmin <= longitude <= xmax and ymin <= latitude <= ymax):
        return False
    starts = list(shape.parts) + [len(shape.points)]
    inside = False
    for start, end in zip(starts, starts[1:]):
        ring = shape.points[start:end]
        if len(ring) >= 3 and ring_contains(longitude, latitude, ring):
            inside = not inside
    return inside


def load_hms_year(year: int) -> tuple[dict[str, list[shapefile.Shape]], str, str, int]:
    by_day: dict[str, list[shapefile.Shape]] = defaultdict(list)
    last_polygon_date = ""
    polygon_records = 0
    path = NOAA_HMS_DOWNLOADS / f"hms_smoke{year}.zip"
    if not path.exists():
        raise FileNotFoundError(
            f"missing {path}; run python -m pipeline.download_extension_inputs {year}"
        )
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as temp_dir:
        archive.extractall(temp_dir)
        shape_path = next(Path(temp_dir).rglob(f"hms_smoke{year}.shp"))
        reader = shapefile.Reader(str(shape_path))
        fields = [field[0] for field in reader.fields[1:]]
        for shape_record in reader.iterShapeRecords():
            polygon_records += 1
            record = dict(zip(fields, shape_record.record))
            start = parse_hms_datetime(str(record["Start"]))
            end = parse_hms_datetime(str(record["End"]))
            cursor = start.date()
            while cursor <= end.date():
                if cursor.year == year:
                    by_day[cursor.isoformat()].append(shape_record.shape)
                cursor += timedelta(days=1)
            if end.year == year:
                last_polygon_date = max(last_polygon_date, end.date().isoformat())
    # A completed annual bundle covers the calendar year even when the final
    # days contain no smoke polygons. For the current year, the latest polygon
    # date remains the operational coverage boundary.
    coverage_through = f"{year}-12-31" if year <= FULL_YEAR_END else last_polygon_date
    return by_day, coverage_through, last_polygon_date, polygon_records


def iter_scope_dates(year: int, data_through: str):
    cursor = date(year, 1, 1)
    end = date.fromisoformat(data_through)
    while cursor <= end:
        yield cursor.isoformat()
        cursor += timedelta(days=1)


def identify_balanced_panel() -> tuple[set[str], dict[int, AqsLoadAudit]]:
    site_year_days: dict[str, dict[int, int]] = defaultdict(dict)
    audits: dict[int, AqsLoadAudit] = {}
    for year in BALANCED_PANEL_YEARS:
        monitor_days, audit = load_aqs_year(year)
        audits[year] = audit
        counts: dict[str, int] = defaultdict(int)
        for _, site in monitor_days:
            counts[site] += 1
        required = math.ceil((date(year, 12, 31).timetuple().tm_yday) * BALANCED_PANEL_MIN_COVERAGE)
        for site, count in counts.items():
            if count >= required:
                site_year_days[site][year] = count
        print(f"profiled AQS {year}: {len(monitor_days):,} site-days")
    panel = {
        site for site, years in site_year_days.items()
        if all(year in years for year in BALANCED_PANEL_YEARS)
    }
    return panel, audits


def percentile(values: list[int], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_rows(
    year: int,
    rows: list[dict[str, object]],
    status: str,
    model_id: str,
    monitor_source_tier: str,
) -> dict[str, object]:
    peak = max(rows, key=lambda row: int(row["indicative_county_population"]))
    balanced_peak = max(rows, key=lambda row: int(row["balanced_indicative_county_population"]))
    return {
        "year": year,
        "metric_id": "smoke_coincident_observed_high_pm25_monitored_county_screen",
        "model_id": model_id,
        "status": status,
        "monitor_source_tier": monitor_source_tier,
        "as_of_date": rows[-1]["date"],
        "calendar_days_in_scope": len(rows),
        "days_with_valid_monitor_data": sum(int(row["valid_monitor_sites"]) > 0 for row in rows),
        "high_pm25_monitor_days": sum(int(row["high_pm25_monitor_sites"]) > 0 for row in rows),
        "smoke_coincident_high_pm25_monitor_site_days": sum(int(row["smoke_coincident_high_pm25_monitor_sites"]) for row in rows),
        "smoke_coincident_high_pm25_county_days": sum(int(row["smoke_coincident_counties"]) for row in rows),
        "broad_proxy_days_10m": sum(int(row["broad_proxy_day_10m"]) for row in rows),
        "indicative_county_population_days": sum(int(row["indicative_county_population"]) for row in rows),
        "peak_indicative_county_population": int(peak["indicative_county_population"]),
        "peak_date": peak["date"] if int(peak["indicative_county_population"]) else "",
        "event_included_monitor_site_days": sum(int(row["event_included_monitor_sites"]) for row in rows),
        "event_included_smoke_coincident_high_pm25_site_days": sum(int(row["event_included_smoke_coincident_high_pm25_monitor_sites"]) for row in rows),
        "balanced_panel_smoke_coincident_high_pm25_site_days": sum(int(row["balanced_smoke_coincident_high_pm25_monitor_sites"]) for row in rows),
        "balanced_panel_broad_proxy_days_10m": sum(int(row["balanced_broad_proxy_day_10m"]) for row in rows),
        "balanced_panel_indicative_county_population_days": sum(int(row["balanced_indicative_county_population"]) for row in rows),
        "balanced_panel_peak_indicative_county_population": int(balanced_peak["balanced_indicative_county_population"]),
        "balanced_panel_peak_date": balanced_peak["date"] if int(balanced_peak["balanced_indicative_county_population"]) else "",
        "conceptually_consistent_screen": "true",
        "specific_fire_qualifier_codes_available": "false",
        "comparable_to_stanford": "false",
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):,} rows to {path}")


def main() -> None:
    populations = load_county_population()
    national_population = sum(populations.values())
    balanced_panel, first_pass_audits = identify_balanced_panel()
    if not balanced_panel:
        raise ValueError("strict 2006-2025 balanced monitor panel is empty")

    daily_rows: list[dict[str, object]] = []
    annual_rows: list[dict[str, object]] = []
    same_cutoff_rows: list[dict[str, object]] = []
    coverage_rows: list[dict[str, object]] = []
    source_audits: list[dict[str, object]] = []

    for year in YEARS:
        monitor_days, aqs_audit = load_aqs_year(year)
        airnow_through = ""
        airnow_start = ""
        model_id = MODEL_ID
        monitor_source_tier = "final_aqs_daily"
        if year == LAST_YEAR:
            airnow_days, airnow_through = load_airnow_supplement()
            monitor_days.update(airnow_days)
            airnow_start = AIRNOW_SUPPLEMENT_START_DATE
            model_id = COMPOSITE_MODEL_ID
            monitor_source_tier = "final_aqs_plus_preliminary_airnow"
        smoke_by_day, hms_through, hms_last_polygon_date, hms_polygon_records = load_hms_year(year)
        monitor_through = max(aqs_audit.data_through, airnow_through)
        common_through = min(monitor_through, hms_through)
        monitors_by_day: dict[str, list[tuple[str, dict[str, object]]]] = defaultdict(list)
        for (day, site), observation in monitor_days.items():
            if day <= common_through:
                monitors_by_day[day].append((site, observation))

        year_rows: list[dict[str, object]] = []
        monitored_counties_all: set[str] = set()
        qualifying_counties_all: set[str] = set()
        sites_all: set[str] = set()
        daily_site_counts: list[int] = []
        for day in iter_scope_dates(year, common_through):
            observations = monitors_by_day.get(day, [])
            sites_all.update(site for site, _ in observations)
            monitored_counties = {str(item["county"]) for _, item in observations}
            monitored_counties_all.update(monitored_counties)
            daily_site_counts.append(len(observations))
            high = [(site, item) for site, item in observations if float(item["pm25"]) >= PM25_THRESHOLD]
            polygons = smoke_by_day.get(day, [])
            coincident: list[tuple[str, dict[str, object]]] = []
            for site, item in high:
                if any(shape_contains(shape, float(item["longitude"]), float(item["latitude"])) for shape in polygons):
                    coincident.append((site, item))
            coincident_sites = {site for site, _ in coincident}
            coincident_counties = {str(item["county"]) for _, item in coincident}
            qualifying_counties_all.update(coincident_counties)
            indicative_population = sum(populations.get(county, 0) for county in coincident_counties)

            balanced_observations = [(site, item) for site, item in observations if site in balanced_panel]
            balanced_high = [(site, item) for site, item in high if site in balanced_panel]
            balanced_coincident = [(site, item) for site, item in coincident if site in balanced_panel]
            balanced_counties = {str(item["county"]) for _, item in balanced_coincident}
            balanced_population = sum(populations.get(county, 0) for county in balanced_counties)
            event_included_sites = {site for site, item in observations if bool(item["event_included"])}
            event_included_coincident = {
                site for site, item in coincident if bool(item["event_included"])
            }

            row = {
                "date": day,
                "year": year,
                "model_id": model_id,
                "monitor_source_tier": (
                    "preliminary_airnow" if year == LAST_YEAR and day >= airnow_start else "final_aqs_daily"
                ),
                "valid_monitor_sites": len(observations),
                "monitored_counties": len(monitored_counties),
                "monitored_county_population": sum(populations.get(county, 0) for county in monitored_counties),
                "high_pm25_monitor_sites": len(high),
                "smoke_coincident_high_pm25_monitor_sites": len(coincident_sites),
                "smoke_coincident_counties": len(coincident_counties),
                "indicative_county_population": indicative_population,
                "broad_proxy_day_10m": int(indicative_population >= BROAD_POPULATION),
                "event_included_monitor_sites": len(event_included_sites),
                "event_included_smoke_coincident_high_pm25_monitor_sites": len(event_included_coincident),
                "balanced_valid_monitor_sites": len(balanced_observations),
                "balanced_high_pm25_monitor_sites": len(balanced_high),
                "balanced_smoke_coincident_high_pm25_monitor_sites": len(balanced_coincident),
                "balanced_smoke_coincident_counties": len(balanced_counties),
                "balanced_indicative_county_population": balanced_population,
                "balanced_broad_proxy_day_10m": int(balanced_population >= BROAD_POPULATION),
                "comparable_to_stanford": "false",
            }
            year_rows.append(row)
            daily_rows.append(row)

        full_year = common_through == f"{year}-12-31"
        annual = summarize_rows(
            year,
            year_rows,
            "calendar_year_snapshot_revisionable" if full_year else "year_to_date_composite_snapshot",
            model_id,
            monitor_source_tier,
        )
        annual.update({
            "aqs_data_through": aqs_audit.data_through,
            "airnow_supplement_start": airnow_start,
            "airnow_data_through": airnow_through,
            "hms_data_through": hms_through,
            "hms_last_polygon_date": hms_last_polygon_date,
            "monitored_sites": len(sites_all),
            "monitored_counties": len(monitored_counties_all),
            "qualifying_counties": len(qualifying_counties_all),
            "balanced_panel_sites_defined": len(balanced_panel),
            "balanced_panel_sites_observed": len(sites_all & balanced_panel),
        })
        annual_rows.append(annual)

        same_end = date(year, *SAME_CUTOFF_MONTH_DAY).isoformat()
        window_rows = [row for row in year_rows if str(row["date"]) <= same_end]
        if len(window_rows) != (date(year, *SAME_CUTOFF_MONTH_DAY) - date(year, 1, 1)).days + 1:
            raise ValueError(f"incomplete Jan 1-Jul 18 window for {year}")
        same = summarize_rows(
            year,
            window_rows,
            "fixed_window_jan01_jul18",
            model_id,
            monitor_source_tier,
        )
        same.update({
            "window_start": f"{year}-01-01",
            "window_end": same_end,
            "identical_monitor_source_to_2026": "true" if year == LAST_YEAR else "false",
            "balanced_panel_sites_defined": len(balanced_panel),
            "balanced_panel_sites_observed": len({site for day, site in monitor_days if day <= same_end} & balanced_panel),
        })
        same_cutoff_rows.append(same)

        monitored_population = sum(populations.get(county, 0) for county in monitored_counties_all)
        coverage_rows.append({
            "year": year,
            "scope_start": f"{year}-01-01",
            "scope_end": common_through,
            "calendar_days": len(year_rows),
            "days_with_any_valid_site": sum(count > 0 for count in daily_site_counts),
            "distinct_monitor_sites": len(sites_all),
            "distinct_monitored_counties": len(monitored_counties_all),
            "distinct_monitored_states_dc": len({county[:2] for county in monitored_counties_all}),
            "monitor_site_days": sum(daily_site_counts),
            "mean_valid_sites_per_day": round(statistics.fmean(daily_site_counts), 3),
            "p10_valid_sites_per_day": round(percentile(daily_site_counts, 0.10), 3),
            "p50_valid_sites_per_day": round(percentile(daily_site_counts, 0.50), 3),
            "p90_valid_sites_per_day": round(percentile(daily_site_counts, 0.90), 3),
            "monitored_county_population_reference": monitored_population,
            "monitored_county_population_share_pct": round(monitored_population / national_population * 100.0, 3),
            "balanced_panel_sites_defined": len(balanced_panel),
            "balanced_panel_sites_observed": len(sites_all & balanced_panel),
            "hms_days_with_polygons": sum(bool(smoke_by_day.get(day)) for day in iter_scope_dates(year, common_through)),
            "hms_polygon_records": hms_polygon_records,
        })
        source_audits.append({
            "year": year,
            "aqs": aqs_audit.__dict__,
            "hms_data_through": hms_through,
            "hms_last_polygon_date": hms_last_polygon_date,
            "hms_polygon_records": hms_polygon_records,
            "airnow_data_through": airnow_through,
        })
        print(f"processed {year}: {len(year_rows)} days, {len(sites_all):,} sites")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    write_csv(PROCESSED / "operational_smoke_screen_daily_2006_2026.csv", daily_rows)
    write_csv(PROCESSED / "operational_smoke_screen_annual_2006_2026.csv", annual_rows)
    write_csv(PROCESSED / "operational_smoke_screen_same_cutoff_2006_2026.csv", same_cutoff_rows)
    write_csv(PROCESSED / "operational_smoke_screen_monitor_coverage_2006_2026.csv", coverage_rows)

    # Preserve stable 2024–2026 filenames for existing consumers.
    legacy_daily = [row for row in daily_rows if int(row["year"]) >= 2024]
    legacy_annual = [row for row in annual_rows if int(row["year"]) >= 2024]
    write_csv(PROCESSED / "operational_smoke_proxy_daily_2024_2026.csv", legacy_daily)
    write_csv(PROCESSED / "operational_smoke_proxy_annual_2024_2026.csv", legacy_annual)

    audit = {
        "model_id": MODEL_ID,
        "years": [FIRST_YEAR, LAST_YEAR],
        "threshold_pm25_ug_m3": PM25_THRESHOLD,
        "minimum_observation_percent": MIN_OBSERVATION_PERCENT,
        "aqs_event_policy": {
            "included_daily_summary_event_types": sorted(INCLUDED_EVENT_TYPES),
            "excluded_daily_summary_variants_are_ignored": True,
            "specific_fire_qualifier_codes_available_in_bulk_daily_files": False,
            "interpretation": (
                "Included summaries preserve event-affected measurements, but the bulk daily "
                "files do not identify RF Canadian fire, RT U.S. wildfire, or RM prescribed "
                "fire codes. HMS overlap supplies smoke presence, not fire origin."
            ),
        },
        "balanced_panel": {
            "definition_years": [BALANCED_PANEL_YEARS[0], BALANCED_PANEL_YEARS[-1]],
            "minimum_valid_day_share_each_year": BALANCED_PANEL_MIN_COVERAGE,
            "site_count": len(balanced_panel),
            "site_ids": sorted(balanced_panel),
        },
        "source_audits": source_audits,
        "first_pass_reconciles": all(
            first_pass_audits[year].selected_site_days
            == next(item["aqs"]["selected_site_days"] for item in source_audits if item["year"] == year)
            for year in BALANCED_PANEL_YEARS
        ),
        "comparability": {
            "stanford": False,
            "reason": (
                "This screen uses observed total PM2.5 at monitored points plus HMS presence; "
                "Stanford estimates wildfire-attributable PM2.5 for all counties."
            ),
            "same_cutoff_2026_monitor_source_break": (
                "The 2026 fixed window supplements lagged AQS with preliminary AirNow after "
                f"{AIRNOW_SUPPLEMENT_START_DATE}; older years use final AQS daily summaries."
            ),
        },
    }
    audit_path = PROCESSED / "operational_smoke_screen_audit_2006_2026.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(f"wrote {audit_path}")


if __name__ == "__main__":
    main()
