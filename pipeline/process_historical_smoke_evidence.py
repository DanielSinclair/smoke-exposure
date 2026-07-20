#!/usr/bin/env python3
"""Build normalized pre-2006 documentary smoke evidence and search coverage.

The product answers "what has been documented?", not "how much smoke occurred?".
It preserves unknown months, separates observations from interpreted events,
and treats NOAA Storm Events as a candidate/corroboration screen only.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
import gzip
import json
from pathlib import Path

from pipeline.settings import (
    HISTORICAL_SMOKE_EVIDENCE,
    NOAA_STORM_EVENTS_1950_2005,
    PROCESSED,
    ROOT,
)


EVENT_FIELDS = [
    "event_id", "start_date", "end_date", "event_name", "source_fire_names",
    "origin_country", "origin_regions", "impacted_us_states", "impacted_us_regions",
    "evidence_level", "attribution_confidence", "quantified_pm25_or_aqi",
    "quantitatively_comparable", "primary_source_ids", "review_status", "notes",
]
OBSERVATION_FIELDS = [
    "observation_id", "event_id", "observation_date", "evidence_type",
    "location_scope", "measurement_or_description", "source_id",
    "independent_source_group",
]
SOURCE_FIELDS = [
    "source_id", "title", "organization", "publication_date", "url",
    "source_type", "authority", "license_or_use", "notes",
]
SEARCH_FIELDS = [
    "year", "month", "month_start", "review_status", "documented_event_count",
    "source_layers_checked", "source_layer_coverage", "absence_interpretation",
    "quantitatively_comparable",
]
STORM_FIELDS = [
    "storm_event_id", "year", "start_date", "end_date", "state", "location",
    "event_type", "narrative_smoke_signal", "matched_terms", "source_file",
    "role", "quantitatively_comparable",
]
BOOLEAN_FIELDS = {"quantified_pm25_or_aqi", "quantitatively_comparable"}
ATTRIBUTION_VALUES = {"confirmed", "probable", "possible", "unknown"}
REVIEW_VALUES = {"accepted", "rejected", "candidate"}
SMOKE_TERMS = ("smoke", "haze", "air quality", "visibility")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_contracts(
    events: list[dict[str, str]], observations: list[dict[str, str]], sources: list[dict[str, str]]
) -> None:
    def require_schema(rows: list[dict[str, str]], expected: list[str], name: str) -> None:
        if not rows or list(rows[0]) != expected:
            raise ValueError(f"{name} must be non-empty and use the documented schema")

    require_schema(events, EVENT_FIELDS, "events")
    require_schema(observations, OBSERVATION_FIELDS, "observations")
    require_schema(sources, SOURCE_FIELDS, "sources")
    event_ids = [row["event_id"] for row in events]
    observation_ids = [row["observation_id"] for row in observations]
    source_ids = [row["source_id"] for row in sources]
    for name, identifiers in (
        ("event", event_ids), ("observation", observation_ids), ("source", source_ids)
    ):
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"duplicate {name} identifier")
    event_set, source_set = set(event_ids), set(source_ids)
    for row in events:
        start, end = date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])
        if not (date(1950, 1, 1) <= start <= end <= date(2005, 12, 31)):
            raise ValueError(f"event outside 1950-2005: {row['event_id']}")
        if not 1 <= int(row["evidence_level"]) <= 4:
            raise ValueError(f"invalid documentary evidence level: {row['event_id']}")
        if row["attribution_confidence"] not in ATTRIBUTION_VALUES:
            raise ValueError(f"invalid attribution confidence: {row['event_id']}")
        if row["review_status"] not in REVIEW_VALUES:
            raise ValueError(f"invalid review status: {row['event_id']}")
        if row["quantitatively_comparable"] != "false":
            raise ValueError("pre-2006 documentary events must never be marked comparable")
        if any(row[field] not in {"true", "false"} for field in BOOLEAN_FIELDS):
            raise ValueError(f"invalid boolean in {row['event_id']}")
        missing = set(row["primary_source_ids"].split("|")) - source_set
        if missing:
            raise ValueError(f"event {row['event_id']} has unknown sources: {sorted(missing)}")
    for row in observations:
        if row["event_id"] not in event_set or row["source_id"] not in source_set:
            raise ValueError(f"orphan observation: {row['observation_id']}")
        date.fromisoformat(row["observation_date"])
    observed_events = {row["event_id"] for row in observations}
    if observed_events != event_set:
        raise ValueError(f"events without observations: {sorted(event_set - observed_events)}")
    if any(not row["url"].startswith("https://") for row in sources):
        raise ValueError("every historical evidence source needs an HTTPS URL")
    observation_types: dict[str, set[str]] = {}
    for row in observations:
        observation_types.setdefault(row["event_id"], set()).add(row["evidence_type"])
    for row in events:
        if int(row["evidence_level"]) < 2:
            continue
        source_count = len(set(row["primary_source_ids"].split("|")))
        direct_multi_observation = any(
            marker in evidence_type
            for evidence_type in observation_types[row["event_id"]]
            for marker in ("station_survey", "regulatory_monitor", "satellite_and_monitor")
        )
        if source_count < 2 and not direct_multi_observation:
            raise ValueError(
                f"level 2+ event lacks multiple sources or direct multi-observation evidence: {row['event_id']}"
            )


def process_storm_events() -> tuple[list[dict[str, object]], set[int]]:
    output: list[dict[str, object]] = []
    screened_years: set[int] = set()
    receipt = json.loads((NOAA_STORM_EVENTS_1950_2005 / "receipt.json").read_text())
    receipt_files = receipt["files"]
    if sorted(int(record["year"]) for record in receipt_files) != list(range(1950, 2006)):
        raise ValueError("NOAA Storm Events receipt must cover every annual file from 1950-2005")
    for record in receipt_files:
        path = ROOT / record["local_path"]
        if not path.exists():
            raise FileNotFoundError(
                f"missing NOAA Storm Events input {path}; run pipeline.download_historical_smoke_inputs"
            )
        with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                year = int(row["YEAR"])
                if row["EVENT_TYPE"].strip().lower() != "wildfire":
                    continue
                screened_years.add(year)
                narrative = " ".join((row.get("EPISODE_NARRATIVE", ""), row.get("EVENT_NARRATIVE", ""))).lower()
                matched = [term for term in SMOKE_TERMS if term in narrative]
                start = datetime.strptime(row["BEGIN_DATE_TIME"].split()[0], "%d-%b-%y").date()
                end = datetime.strptime(row["END_DATE_TIME"].split()[0], "%d-%b-%y").date()
                output.append({
                    "storm_event_id": row["EVENT_ID"],
                    "year": year,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "state": row["STATE"],
                    "location": row.get("CZ_NAME", ""),
                    "event_type": row["EVENT_TYPE"],
                    "narrative_smoke_signal": str(bool(matched)).lower(),
                    "matched_terms": "|".join(matched),
                    "source_file": path.name,
                    "role": "incident_candidate_or_corroboration_only",
                    "quantitatively_comparable": "false",
                })
    return sorted(output, key=lambda row: (row["year"], row["start_date"], row["storm_event_id"])), screened_years


def search_coverage(
    events: list[dict[str, str]], storm_screened_years: set[int]
) -> list[dict[str, object]]:
    counts: dict[tuple[int, int], int] = {}
    for row in events:
        cursor = date.fromisoformat(row["start_date"])
        end = date.fromisoformat(row["end_date"])
        while cursor <= end:
            key = (cursor.year, cursor.month)
            counts[key] = counts.get(key, 0) + 1
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    output = []
    for year in range(1950, 2006):
        for month in range(1, 13):
            event_count = counts.get((year, month), 0)
            layers = ["curated_government_and_peer_reviewed_event_sources_v1"]
            if year in storm_screened_years:
                layers.append("noaa_storm_events_wildfire_candidate_screen")
            output.append({
                "year": year,
                "month": month,
                "month_start": f"{year:04d}-{month:02d}-01",
                "review_status": (
                    "documented_case_found" if event_count else
                    "candidate_screen_complete_not_exhaustive" if year in storm_screened_years else
                    "not_systematically_reviewed"
                ),
                "documented_event_count": event_count,
                "source_layers_checked": "|".join(layers),
                "source_layer_coverage": (
                    "NOAA Storm Events Wildfire event type plus curated v1 sources; narratives are incomplete"
                    if year in storm_screened_years else
                    "Curated v1 sources only; NOAA Storm Events did not provide Wildfire as a uniform event type"
                ),
                "absence_interpretation": (
                    "documented_case_present" if event_count else
                    "no_qualifying_case_in_screened_sources_not_no_smoke" if year in storm_screened_years else
                    "unknown_not_zero"
                ),
                "quantitatively_comparable": "false",
            })
    return output


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    events = read_csv(HISTORICAL_SMOKE_EVIDENCE / "events.csv")
    observations = read_csv(HISTORICAL_SMOKE_EVIDENCE / "observations.csv")
    sources = read_csv(HISTORICAL_SMOKE_EVIDENCE / "sources.csv")
    validate_contracts(events, observations, sources)
    events.sort(key=lambda row: (row["start_date"], row["event_id"]))
    observations.sort(key=lambda row: (row["observation_date"], row["observation_id"]))
    sources.sort(key=lambda row: row["source_id"])
    storm_candidates, screened_years = process_storm_events()
    ledger = search_coverage(events, screened_years)
    write_csv(PROCESSED / "historical_smoke_events_1950_2005.csv", events, EVENT_FIELDS)
    write_csv(PROCESSED / "historical_smoke_observations_1950_2005.csv", observations, OBSERVATION_FIELDS)
    write_csv(PROCESSED / "historical_smoke_sources.csv", sources, SOURCE_FIELDS)
    write_csv(PROCESSED / "historical_smoke_search_coverage_1950_2005.csv", ledger, SEARCH_FIELDS)
    write_csv(PROCESSED / "noaa_storm_events_wildfire_candidates_1950_2005.csv", storm_candidates, STORM_FIELDS)
    print(
        f"wrote {len(events)} historical events, {len(observations)} observations, "
        f"{len(sources)} sources, {len(ledger)} month statuses, and "
        f"{len(storm_candidates)} NOAA wildfire candidates"
    )


if __name__ == "__main__":
    main()
