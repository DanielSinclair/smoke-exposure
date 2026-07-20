#!/usr/bin/env python3
"""Aggregate the Stanford ECHO v2 county-day beta into annual U.S. metrics."""

from __future__ import annotations

import csv
import json
from collections import defaultdict

from pipeline.settings import CENSUS_2020, PROCESSED, STANFORD_V2


SMOKE_CSV = STANFORD_V2 / "smokePM2pt5_predictions_daily_county_20060101-20231231.csv"
POP_CSV = CENSUS_2020 / "co-est2020-alldata.csv"
PRIMARY_PM25 = 35.5
PRIMARY_POPULATION = 10_000_000
PM25_THRESHOLDS = (25.0, 35.5, 50.0)
POPULATION_THRESHOLDS = (5_000_000, 10_000_000, 25_000_000)
EXCLUDED_STATE_FIPS = {"02", "15"}


def load_population() -> dict[str, int]:
    populations: dict[str, int] = {}
    with POP_CSV.open(newline="", encoding="latin-1") as handle:
        for row in csv.DictReader(handle):
            if row["SUMLEV"] != "050":
                continue
            state = row["STATE"].zfill(2)
            if state in EXCLUDED_STATE_FIPS or int(state) > 56:
                continue
            populations[state + row["COUNTY"].zfill(3)] = int(row["POPESTIMATE2020"])
    return populations


def main() -> None:
    populations = load_population()
    daily_by_threshold: dict[float, dict[str, int]] = {
        threshold: defaultdict(int) for threshold in PM25_THRESHOLDS
    }
    counties_by_date: dict[str, set[str]] = defaultdict(set)
    source_dates: set[str] = set()
    unmatched_geoids: set[str] = set()
    parsed_rows = 0
    positive_rows = 0

    with SMOKE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            parsed_rows += 1
            geoid = row["GEOID"].zfill(5)
            if geoid not in populations:
                unmatched_geoids.add(geoid)
                continue
            raw_date = row["date"]
            date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
            source_dates.add(date)
            smoke_pm25 = float(row["smokePM_pred"])
            positive_rows += smoke_pm25 > 0
            for threshold in PM25_THRESHOLDS:
                if smoke_pm25 >= threshold:
                    daily_by_threshold[threshold][date] += populations[geoid]
            if smoke_pm25 >= PRIMARY_PM25:
                counties_by_date[date].add(geoid)

    all_dates = sorted(source_dates)
    daily_path = PROCESSED / "stanford_daily_smoke_2006_2023.csv"
    with daily_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "date", "year", "population_exposed_pm25_ge_25",
            "population_exposed_pm25_ge_35_5", "population_exposed_pm25_ge_50",
            "counties_pm25_ge_35_5", "broad_day_10m",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for date in all_dates:
            exposed = daily_by_threshold[PRIMARY_PM25].get(date, 0)
            writer.writerow({
                "date": date,
                "year": date[:4],
                "population_exposed_pm25_ge_25": daily_by_threshold[25.0].get(date, 0),
                "population_exposed_pm25_ge_35_5": exposed,
                "population_exposed_pm25_ge_50": daily_by_threshold[50.0].get(date, 0),
                "counties_pm25_ge_35_5": len(counties_by_date.get(date, set())),
                "broad_day_10m": int(exposed >= PRIMARY_POPULATION),
            })

    annual_rows: list[dict[str, object]] = []
    sensitivity_rows: list[dict[str, object]] = []
    for year in range(2006, 2024):
        dates = [date for date in all_dates if date.startswith(str(year))]
        daily = [(date, daily_by_threshold[PRIMARY_PM25].get(date, 0)) for date in dates]
        peak_date, peak = max(daily, key=lambda item: item[1], default=("", 0))
        exposed_counties = set().union(*(counties_by_date.get(date, set()) for date in dates))
        annual_rows.append({
            "year": year,
            "broad_high_aqi_smoke_days_10m": sum(pop >= PRIMARY_POPULATION for _, pop in daily),
            "population_days_aqi101plus_millions": round(sum(pop for _, pop in daily) / 1_000_000, 3),
            "residents_exposed_at_least_once_millions": round(
                sum(populations[geoid] for geoid in exposed_counties) / 1_000_000, 3
            ),
            "maximum_daily_population_exposed_millions": round(peak / 1_000_000, 3),
            "maximum_exposure_date": peak_date if peak else "",
            "counties_exposed_at_least_once": len(exposed_counties),
        })
        sensitivity: dict[str, object] = {"year": year}
        for threshold in POPULATION_THRESHOLDS:
            sensitivity[f"days_pm25_ge_35_5_pop_ge_{threshold // 1_000_000}m"] = sum(
                pop >= threshold for _, pop in daily
            )
        for threshold in PM25_THRESHOLDS:
            label = str(threshold).replace(".", "_")
            sensitivity[f"days_pm25_ge_{label}_pop_ge_10m"] = sum(
                daily_by_threshold[threshold].get(date, 0) >= PRIMARY_POPULATION for date in dates
            )
        sensitivity_rows.append(sensitivity)

    for filename, output_rows in (
        ("stanford_annual_smoke_2006_2023.csv", annual_rows),
        ("stanford_metric_sensitivity_2006_2023.csv", sensitivity_rows),
    ):
        with (PROCESSED / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=list(output_rows[0]),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(output_rows)

    audit = {
        "source_rows_parsed": parsed_rows,
        "source_positive_smoke_rows": positive_rows,
        "source_date_min": min(all_dates),
        "source_date_max": max(all_dates),
        "population_counties": len(populations),
        "population_total_conus_2020_estimate": sum(populations.values()),
        "unmatched_source_geoids": sorted(unmatched_geoids),
        "primary_pm25_threshold_ug_m3": PRIMARY_PM25,
        "primary_population_threshold": PRIMARY_POPULATION,
        "population_basis": "Fixed July 1, 2020 Census Vintage 2020 county estimate",
    }
    (PROCESSED / "stanford_aggregation_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(f"wrote {len(annual_rows)} annual rows and {len(all_dates)} daily rows")


if __name__ == "__main__":
    main()
