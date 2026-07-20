#!/usr/bin/env python3
"""Build annual fire and smoke-region context without claiming attribution.

The fire records identify large fires that occurred in a year. They are useful
tooltip context, but are not linked causally to the modeled U.S. smoke burden.
The impacted-state table is calculated directly from the same Stanford county
file and fixed 2020 population used by the comparable national series.
Pre-2006 episodes are a sparse documentation table, never a zero-filled series.
"""

from __future__ import annotations

from collections import defaultdict
import csv
import io
from pathlib import Path
import tempfile
import zipfile

import shapefile

from pipeline.settings import (
    AQI_101_PM25_UG_M3,
    CENSUS_2020,
    MTBS_SOURCE,
    NRCAN_NFDB_LARGE_FIRES_SOURCE,
    PROCESSED,
    STANFORD_V2,
)


STATE_NAMES = {
    "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
    "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
    "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
    "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa", "20": "Kansas",
    "21": "Kentucky", "22": "Louisiana", "23": "Maine", "24": "Maryland",
    "25": "Massachusetts", "26": "Michigan", "27": "Minnesota", "28": "Mississippi",
    "29": "Missouri", "30": "Montana", "31": "Nebraska", "32": "Nevada",
    "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico", "36": "New York",
    "37": "North Carolina", "38": "North Dakota", "39": "Ohio", "40": "Oklahoma",
    "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
    "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
    "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
    "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming",
}

STATE_ABBREVIATIONS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

CANADA_REGIONS = {
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba",
    "NB": "New Brunswick", "NL": "Newfoundland and Labrador", "NS": "Nova Scotia",
    "NT": "Northwest Territories", "NU": "Nunavut", "ON": "Ontario",
    "PE": "Prince Edward Island", "QC": "Quebec", "SK": "Saskatchewan", "YT": "Yukon",
    "PC": "Parks Canada",
}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def normalized_name(value: object) -> str:
    name = " ".join(str(value or "").strip().split())
    if name.upper() in {"", "UNNAMED", "UNKNOWN", "N/A", "NONE"}:
        return ""
    return name.title() if name.isupper() else name


def load_mtbs_context() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
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
            if not ignition:
                continue
            fire_id = str(row.get("FIRE_ID", "")).strip()
            candidate = {
                "normalized_record_id": f"mtbs:{fire_id}",
                "year": ignition.year,
                "geography": "United States",
                "fire_name": normalized_name(row.get("FIRE_NAME")),
                "source_record_id": fire_id,
                "incident_id": fire_id,
                "region": STATE_ABBREVIATIONS.get(fire_id[:2], fire_id[:2] or "Unknown"),
                "latitude": float(row.get("LATITUDE") or 0),
                "longitude": float(row.get("LONGITUDE") or 0),
                "acres": round(float(row.get("ACRES") or 0)),
                "coverage_scope": "MTBS mapped wildfire: at least 500 acres in the East or 1,000 acres in the West",
                "source_year_status": (
                    "provisional_incomplete" if ignition.year >= 2025 else "complete_release_year"
                ),
                "source_coverage_complete": str(ignition.year <= 2024).lower(),
                "source_release": "2026-06-28",
                "source_dataset": "MTBS Fire Occurrence Points",
                "provisional": str(ignition.year >= 2025).lower(),
            }
            candidate["location_plausible_for_geography"] = str(
                18 <= float(candidate["latitude"]) <= 72
                and -180 <= float(candidate["longitude"]) <= -65
            ).lower()
            records.append(candidate)
    return records


def load_canada_context() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with zipfile.ZipFile(NRCAN_NFDB_LARGE_FIRES_SOURCE) as archive:
        member = next(name for name in archive.namelist() if name.endswith("_large_fires.txt"))
        with archive.open(member) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig"))
            for source_row_number, row in enumerate(reader, 2):
                prescribed = str(row.get("PRESCRIBED", "")).strip().lower()
                fire_type = str(row.get("FIRE_TYPE", "")).strip().lower()
                if prescribed in {"1", "true", "yes", "y"} or "prescribed" in fire_type:
                    continue
                try:
                    year = int(row["YEAR"])
                    acres = round(float(row["SIZE_HA"]) * 2.4710538147)
                except (KeyError, TypeError, ValueError):
                    continue
                if not 1900 <= year <= 2026:
                    continue
                fire_id = str(row.get("NFDBFIREID", "")).strip()
                agency = str(row.get("SRC_AGENCY", "")).strip().upper()
                candidate = {
                    "normalized_record_id": f"nrcan-nfdb:{source_row_number}",
                    "year": year,
                    "geography": "Canada",
                    "fire_name": normalized_name(row.get("FIRENAME")),
                    "source_record_id": fire_id,
                    "incident_id": str(row.get("FIRE_ID", "")).strip() or fire_id,
                    "region": CANADA_REGIONS.get(agency, agency or "Unknown"),
                    "latitude": float(row.get("LATITUDE") or 0),
                    "longitude": float(row.get("LONGITUDE") or 0),
                    "acres": acres,
                    "coverage_scope": "CNFDB reported large-fire point archive: greater than 200 hectares",
                    "source_year_status": "coverage_varies_by_agency_and_year",
                    "source_coverage_complete": "false",
                    "source_release": "2026-05-29",
                    "source_dataset": "Canadian National Fire Database large-fire points",
                    "provisional": "false",
                }
                candidate["location_plausible_for_geography"] = str(
                    41 <= float(candidate["latitude"]) <= 84
                    and -142 <= float(candidate["longitude"]) <= -52
                ).lower()
                records.append(candidate)
    return records


def normalized_large_fire_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    output = []
    for row in records:
        output.append({
            "normalized_record_id": row["normalized_record_id"],
            "year": row["year"],
            "geography": row["geography"],
            "incident_name": row["fire_name"] or row["incident_id"],
            "label_kind": "reported_name" if row["fire_name"] else "agency_incident_id",
            "source_record_id": row["source_record_id"],
            "agency_incident_id": row["incident_id"],
            "region": row["region"],
            "latitude": round(float(row["latitude"]), 5),
            "longitude": round(float(row["longitude"]), 5),
            "location_plausible_for_geography": row["location_plausible_for_geography"],
            "acres": row["acres"],
            "coverage_scope": row["coverage_scope"],
            "source_year_status": row["source_year_status"],
            "source_coverage_complete": row["source_coverage_complete"],
            "source_release": row["source_release"],
            "source_dataset": row["source_dataset"],
            "provisional": row["provisional"],
            "causal_smoke_attribution": "false",
        })
    return sorted(
        output,
        key=lambda row: (
            int(row["year"]), str(row["geography"]), -int(row["acres"]),
            str(row["normalized_record_id"]),
        ),
    )


def annual_large_fire_rollup(records: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in records:
        groups[(int(row["year"]), str(row["geography"]))].append(row)
    output = []
    for (year, geography), items in sorted(groups.items()):
        output.append({
            "year": year,
            "geography": geography,
            "incident_records": len(items),
            "reported_name_records": sum(row["label_kind"] == "reported_name" for row in items),
            "agency_id_only_records": sum(row["label_kind"] == "agency_incident_id" for row in items),
            "acres": sum(int(row["acres"]) for row in items),
            "source_dataset": items[0]["source_dataset"],
            "coverage_scope": items[0]["coverage_scope"],
            "source_year_status": items[0]["source_year_status"],
            "source_coverage_complete": items[0]["source_coverage_complete"],
            "comparable_to_other_geography": "false",
        })
    return output


def select_annual_fire_context(records: list[dict[str, object]]) -> list[dict[str, object]]:
    by_group: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in records:
        if int(row["year"]) < 1950:
            continue
        by_group[(int(row["year"]), str(row["geography"]))].append(row)

    output: list[dict[str, object]] = []
    for (year, geography), candidates in sorted(by_group.items()):
        unique_labels: dict[tuple[str, str], dict[str, object]] = {}
        for row in candidates:
            label = str(row["fire_name"] or row["incident_id"])
            key = (label, str(row["region"]))
            prior = unique_labels.get(key)
            if prior is None or int(row["acres"]) > int(prior["acres"]):
                unique_labels[key] = row
        candidates = list(unique_labels.values())
        named = sorted(
            (row for row in candidates if row["fire_name"]),
            key=lambda row: (-int(row["acres"]), str(row["fire_name"])),
        )
        selected = named[:3]
        if len(selected) < 3:
            selected_ids = {str(row["incident_id"]) for row in selected}
            identified = sorted(
                (row for row in candidates if str(row["incident_id"]) not in selected_ids),
                key=lambda row: (-int(row["acres"]), str(row["incident_id"])),
            )
            selected.extend(identified[: 3 - len(selected)])
        for rank, row in enumerate(selected, 1):
            output.append({
                "year": year,
                "geography": geography,
                "rank": rank,
                "fire_name": row["fire_name"] or row["incident_id"],
                "label_kind": "reported_name" if row["fire_name"] else "agency_incident_id",
                "normalized_record_id": row["normalized_record_id"],
                "source_record_id": row["source_record_id"],
                "region": row["region"],
                "latitude": round(float(row["latitude"]), 5),
                "longitude": round(float(row["longitude"]), 5),
                "acres": row["acres"],
                "source_dataset": row["source_dataset"],
                "provisional": row["provisional"],
                "causal_smoke_attribution": "false",
            })
    return output


def load_county_population() -> dict[str, int]:
    output: dict[str, int] = {}
    with (CENSUS_2020 / "co-est2020-alldata.csv").open(
        newline="", encoding="latin-1"
    ) as handle:
        for row in csv.DictReader(handle):
            if row["SUMLEV"] == "050":
                output[row["STATE"].zfill(2) + row["COUNTY"].zfill(3)] = int(
                    row["POPESTIMATE2020"]
                )
    return output


def load_smoke_region_context() -> list[dict[str, object]]:
    populations = load_county_population()
    daily_state_population: dict[tuple[int, str, str], int] = defaultdict(int)
    source = STANFORD_V2 / "smokePM2pt5_predictions_daily_county_20060101-20231231.csv"
    with source.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                smoke_pm25 = float(row["smokePM_pred"])
            except (KeyError, TypeError, ValueError):
                continue
            if smoke_pm25 < AQI_101_PM25_UG_M3:
                continue
            geoid = row["GEOID"].zfill(5)
            state_fips = geoid[:2]
            if state_fips not in STATE_NAMES:
                continue
            day = row["date"]
            daily_state_population[(int(day[:4]), state_fips, day)] += populations.get(geoid, 0)

    totals: dict[tuple[int, str], dict[str, int]] = defaultdict(
        lambda: {"population_days": 0, "high_smoke_days": 0, "peak_population": 0}
    )
    for (year, state_fips, _day), population in daily_state_population.items():
        summary = totals[(year, state_fips)]
        summary["population_days"] += population
        summary["high_smoke_days"] += 1
        summary["peak_population"] = max(summary["peak_population"], population)

    output: list[dict[str, object]] = []
    years = sorted({year for year, _ in totals})
    for year in years:
        ranked = sorted(
            ((state_fips, values) for (row_year, state_fips), values in totals.items() if row_year == year),
            key=lambda item: (-item[1]["population_days"], item[0]),
        )
        for rank, (state_fips, values) in enumerate(ranked, 1):
            output.append({
                "year": year,
                "rank": rank,
                "state_fips": state_fips,
                "state": STATE_NAMES[state_fips],
                "high_smoke_population_days": values["population_days"],
                "high_smoke_days": values["high_smoke_days"],
                "peak_population_exposed": values["peak_population"],
                "model_id": "STANFORD_ECHO_V2_BETA_COUNTY_FIXED_2020_POP",
            })
    return output


def documented_episodes() -> list[dict[str, object]]:
    """Load the normalized historical evidence product into the legacy site contract."""
    sources: dict[str, dict[str, str]] = {}
    with (PROCESSED / "historical_smoke_sources.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            sources[row["source_id"]] = row
    episodes: list[dict[str, object]] = []
    with (PROCESSED / "historical_smoke_events_1950_2005.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        for row in csv.DictReader(handle):
            primary_source_id = row["primary_source_ids"].split("|")[0]
            source = sources[primary_source_id]
            episodes.append({
                "event_id": row["event_id"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "event": row["event_name"],
                "source_fires": row["source_fire_names"],
                "source_region": row["origin_regions"],
                "impacted_us_regions": row["impacted_us_regions"],
                "evidence": f"Documentary evidence level {row['evidence_level']}; {row['attribution_confidence']} attribution",
                "evidence_level": row["evidence_level"],
                "attribution_confidence": row["attribution_confidence"],
                "impacted_us_states": row["impacted_us_states"],
                "primary_source_ids": row["primary_source_ids"],
                "source_title": source["title"],
                "source_url": source["url"],
                "quantitatively_comparable": "false",
            })
    return episodes


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    source_records = load_mtbs_context() + load_canada_context()
    large_fire_records = normalized_large_fire_records(source_records)
    large_fire_annual = annual_large_fire_rollup(large_fire_records)
    fire_context = select_annual_fire_context(source_records)
    smoke_regions = load_smoke_region_context()
    episodes = documented_episodes()
    write_csv(
        PROCESSED / "large_fire_incidents_source_covered.csv", large_fire_records,
        ["normalized_record_id", "year", "geography", "incident_name", "label_kind", "source_record_id", "agency_incident_id", "region", "latitude", "longitude", "location_plausible_for_geography", "acres", "coverage_scope", "source_year_status", "source_coverage_complete", "source_release", "source_dataset", "provisional", "causal_smoke_attribution"],
    )
    write_csv(
        PROCESSED / "large_fire_incidents_annual_source_covered.csv", large_fire_annual,
        ["year", "geography", "incident_records", "reported_name_records", "agency_id_only_records", "acres", "source_dataset", "coverage_scope", "source_year_status", "source_coverage_complete", "comparable_to_other_geography"],
    )
    write_csv(
        PROCESSED / "fire_year_context.csv", fire_context,
        ["year", "geography", "rank", "fire_name", "label_kind", "normalized_record_id", "source_record_id", "region", "latitude", "longitude", "acres", "source_dataset", "provisional", "causal_smoke_attribution"],
    )
    write_csv(
        PROCESSED / "smoke_region_context_2006_2023.csv", smoke_regions,
        ["year", "rank", "state_fips", "state", "high_smoke_population_days", "high_smoke_days", "peak_population_exposed", "model_id"],
    )
    write_csv(
        PROCESSED / "documented_smoke_episodes_1950_2005.csv", episodes,
        ["event_id", "start_date", "end_date", "event", "source_fires", "source_region", "impacted_us_regions", "evidence", "evidence_level", "attribution_confidence", "impacted_us_states", "primary_source_ids", "source_title", "source_url", "quantitatively_comparable"],
    )
    print(
        f"wrote {len(large_fire_records)} normalized large-fire records, "
        f"{len(large_fire_annual)} annual rollups, {len(fire_context)} tooltip records, "
        f"{len(smoke_regions)} state-year records, and {len(episodes)} documented episodes"
    )


if __name__ == "__main__":
    main()
