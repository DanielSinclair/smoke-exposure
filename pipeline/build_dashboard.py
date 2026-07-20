#!/usr/bin/env python3
"""Assemble compact web-ready JSON from tracked processed tables."""

from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date, timedelta
import json
from pathlib import Path

from pipeline.settings import MANIFEST, PROCESSED, SOURCES


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    current_receipt = json.loads((SOURCES / "current-2026-receipt.json").read_text())
    publication_cutoff = current_receipt["publication_cutoff"]
    cutoff_year = int(publication_cutoff[:4])
    stanford_source = PROCESSED / "stanford_annual_smoke_2006_2023.csv"
    stanford_rows = rows(stanford_source)
    stanford_daily_rows = rows(PROCESSED / "stanford_daily_smoke_2006_2023.csv")
    sensitivity_by_year = {
        int(row["year"]): row
        for row in rows(PROCESSED / "stanford_metric_sensitivity_2006_2023.csv")
    }
    aggregation_audit = json.loads(
        (PROCESSED / "stanford_aggregation_audit.json").read_text()
    )
    fixed_population = int(aggregation_audit["population_total_conus_2020_estimate"])

    annual_smoke = []
    running_record = -1
    for row in stanford_rows:
        year = int(row["year"])
        population_days = round(
            float(row["population_days_aqi101plus_millions"]) * 1_000_000
        )
        record_year = population_days > running_record
        running_record = max(running_record, population_days)
        annual_smoke.append({
            "year": year,
            "broad_smoke_days": int(row["broad_high_aqi_smoke_days_10m"]),
            "population_days": population_days,
            "peak_population_exposed": round(
                float(row["maximum_daily_population_exposed_millions"]) * 1_000_000
            ),
            "peak_date": row["maximum_exposure_date"],
            "residents_exposed_at_least_once": round(
                float(row["residents_exposed_at_least_once_millions"]) * 1_000_000
            ),
            "share_exposed_at_least_once": round(
                float(row["residents_exposed_at_least_once_millions"])
                * 1_000_000 / fixed_population * 100,
                1,
            ),
            "per_capita_smoke_days": round(population_days / fixed_population, 2),
            "counties_exposed_at_least_once": int(row["counties_exposed_at_least_once"]),
            "severe_days_10m": int(
                sensitivity_by_year[year]["days_pm25_ge_50_0_pop_ge_10m"]
            ),
            "record_year": record_year,
        })

    rank_by_year = {
        row["year"]: rank
        for rank, row in enumerate(
            sorted(annual_smoke, key=lambda item: item["population_days"], reverse=True),
            start=1,
        )
    }
    for row in annual_smoke:
        row["burden_rank"] = rank_by_year[row["year"]]

    population_day_values = [row["population_days"] for row in annual_smoke]
    early_average = round(sum(population_day_values[:5]) / 5)
    recent_average = round(sum(population_day_values[-5:]) / 5)
    cumulative_population_days = sum(population_day_values)
    rolling_mean_5yr = [
        {
            "year": annual_smoke[index]["year"],
            "value": round(sum(population_day_values[index - 4:index + 1]) / 5),
        }
        for index in range(4, len(annual_smoke))
    ]
    smoke_trend = {
        "early_period": "2006–2010",
        "recent_period": "2019–2023",
        "early_average_population_days": early_average,
        "recent_average_population_days": recent_average,
        "recent_to_early_multiplier": round(recent_average / early_average, 1),
        "early_per_capita_days": round(early_average / fixed_population, 2),
        "recent_per_capita_days": round(recent_average / fixed_population, 2),
        "fixed_population": fixed_population,
        "cumulative_population_days": cumulative_population_days,
        "cumulative_share_since_2019": round(
            sum(population_day_values[-5:]) / cumulative_population_days * 100
        ),
        "cumulative_share_since_2017": round(
            sum(
                row["population_days"] for row in annual_smoke if row["year"] >= 2017
            ) / cumulative_population_days * 100
        ),
        "rolling_mean_5yr": rolling_mean_5yr,
    }

    top_days_source = sorted(
        stanford_daily_rows,
        key=lambda row: int(row["population_exposed_pm25_ge_35_5"]),
        reverse=True,
    )[:10]
    top_days = [{
        "rank": rank,
        "date": row["date"],
        "population_exposed": int(row["population_exposed_pm25_ge_35_5"]),
        "share_of_population": round(
            int(row["population_exposed_pm25_ge_35_5"]) / fixed_population * 100,
            1,
        ),
    } for rank, row in enumerate(top_days_source, start=1)]

    benchmark_source = max(
        (row for row in stanford_daily_rows if int(row["year"]) <= 2010),
        key=lambda row: int(row["population_exposed_pm25_ge_35_5"]),
    )
    benchmark_population = int(benchmark_source["population_exposed_pm25_ge_35_5"])
    benchmark_exceedances = defaultdict(int)
    for row in stanford_daily_rows:
        year = int(row["year"])
        if year >= 2016 and int(row["population_exposed_pm25_ge_35_5"]) > benchmark_population:
            benchmark_exceedances[year] += 1

    streaks = []
    current_start = None
    current_days = 0
    previous_day = None
    for row in sorted(stanford_daily_rows, key=lambda item: item["date"]):
        day = date.fromisoformat(row["date"])
        qualifies = int(row["broad_day_10m"]) == 1
        if qualifies and previous_day == day - timedelta(days=1) and current_days:
            current_days += 1
        elif qualifies:
            if current_days:
                streaks.append({"start_date": current_start.isoformat(), "days": current_days})
            current_start = day
            current_days = 1
        else:
            if current_days:
                streaks.append({"start_date": current_start.isoformat(), "days": current_days})
            current_start = None
            current_days = 0
        previous_day = day
    if current_days:
        streaks.append({"start_date": current_start.isoformat(), "days": current_days})
    longest_by_year = {}
    for streak in streaks:
        year = int(streak["start_date"][:4])
        if year not in longest_by_year or streak["days"] > longest_by_year[year]["days"]:
            longest_by_year[year] = streak
    longest_streaks = sorted(
        longest_by_year.values(),
        key=lambda row: (-row["days"], row["start_date"]),
    )[:3]

    record_years = []
    running_record = -1
    for row in annual_smoke:
        if row["population_days"] > running_record:
            if row["population_days"] > 50_000_000:
                record_years.append(row["year"])
            running_record = row["population_days"]

    extremes = {
        "top_days": top_days,
        "benchmark_day": {
            "date": benchmark_source["date"],
            "population_exposed": benchmark_population,
            "label": "worst day of 2006–2010",
        },
        "days_exceeding_benchmark_since_2016": sum(benchmark_exceedances.values()),
        "days_exceeding_benchmark_by_year": {
            str(year): count for year, count in sorted(benchmark_exceedances.items())
        },
        "longest_streaks": longest_streaks,
        "record_years": record_years,
    }

    def monthly_burden(period_start: int, period_end: int) -> dict:
        month_totals = [0] * 12
        for row in stanford_daily_rows:
            year = int(row["year"])
            if period_start <= year <= period_end:
                month = int(row["date"][5:7]) - 1
                month_totals[month] += int(row["population_exposed_pm25_ge_35_5"])
        total = sum(month_totals)
        return {
            "period": f"{period_start}–{period_end}",
            "monthly_share": [round(value / total * 100, 1) for value in month_totals],
        }

    notable_years = []
    for notable_year in (2018, 2020, 2023):
        month_totals = [0] * 12
        for row in stanford_daily_rows:
            if int(row["year"]) == notable_year:
                month_totals[int(row["date"][5:7]) - 1] += int(
                    row["population_exposed_pm25_ge_35_5"]
                )
        peak_month_index = max(range(12), key=lambda index: month_totals[index])
        notable_years.append({
            "year": notable_year,
            "month": peak_month_index + 1,
            "share_percent": round(
                month_totals[peak_month_index] / sum(month_totals) * 100,
                1,
            ),
        })
    seasonality = {
        "era_1": monthly_burden(2006, 2015),
        "era_2": monthly_burden(2016, 2023),
        "notable_years": notable_years,
    }

    def empty_history_month(status: str) -> dict[str, object]:
        return {
            "status": status,
            "review_status": "not_reviewed",
            "evidence_level": None,
            "evidence_label": None,
            "observed_days": None,
            "smoke_days": None,
            "broad_days": None,
            "population_days": None,
            "peak_population_exposed": None,
            "events": [],
        }

    history_by_year = {
        year: [empty_history_month("no_comparable_daily_data") for _ in range(12)]
        for year in range(1950, cutoff_year + 1)
    }
    review_status_labels = {
        "not_systematically_reviewed": "not_reviewed",
        "candidate_screen_complete_not_exhaustive": "searched_no_qualifying_case_found",
        "documented_case_found": "reviewed_with_evidence",
    }
    for row in rows(PROCESSED / "historical_smoke_search_coverage_1950_2005.csv"):
        month = history_by_year[int(row["year"])][int(row["month"]) - 1]
        month["review_status"] = review_status_labels[row["review_status"]]

    historical_sources = {
        row["source_id"]: row for row in rows(PROCESSED / "historical_smoke_sources.csv")
    }
    historical_observations: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows(PROCESSED / "historical_smoke_observations_1950_2005.csv"):
        historical_observations[row["event_id"]].append(row)

    evidence_labels = {
        1: "Level 1 · single-source documentary evidence",
        2: "Level 2 · corroborated or government-attributed evidence",
        3: "Level 3 · multiple independent evidence streams",
        4: "Level 4 · quantified local or regional evidence",
    }
    documented_smoke_episodes = []
    for row in rows(PROCESSED / "historical_smoke_events_1950_2005.csv"):
        if row["review_status"] != "accepted":
            continue
        source_ids = [value for value in row["primary_source_ids"].split("|") if value]
        primary_source = historical_sources[source_ids[0]]
        event_observations = historical_observations[row["event_id"]]
        pm25_evidence = [
            observation["measurement_or_description"]
            for observation in event_observations
            if "pm25" in observation["evidence_type"].lower()
            or "pm2.5" in observation["measurement_or_description"].lower()
        ]
        aqi_evidence = [
            observation["measurement_or_description"]
            for observation in event_observations
            if "aqi" in observation["evidence_type"].lower()
            or "air quality index" in observation["measurement_or_description"].lower()
        ]
        level = int(row["evidence_level"])
        episode = {
            "event_id": row["event_id"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "event": row["event_name"],
            "event_name": row["event_name"],
            "source_fires": row["source_fire_names"],
            "source_fire_names": row["source_fire_names"],
            "source_region": row["origin_regions"],
            "impacted_us_states": [
                value.strip() for value in row["impacted_us_states"].split(";") if value.strip()
            ],
            "impacted_us_regions": row["impacted_us_regions"],
            "evidence": row["notes"],
            "evidence_level": level,
            "evidence_label": evidence_labels[level],
            "attribution_confidence": row["attribution_confidence"],
            "pm25_metric": " ".join(pm25_evidence) or None,
            "aqi_metric": " ".join(aqi_evidence) or None,
            "source_title": primary_source["title"],
            "source_url": primary_source["url"],
            "source_ids": source_ids,
            "quantitatively_comparable": row["quantitatively_comparable"].lower() == "true",
        }
        documented_smoke_episodes.append(episode)
        start = date.fromisoformat(row["start_date"])
        end = date.fromisoformat(row["end_date"])
        cursor = date(start.year, start.month, 1)
        while cursor <= end:
            month = history_by_year[cursor.year][cursor.month - 1]
            month["review_status"] = "reviewed_with_evidence"
            month["evidence_level"] = max(int(month["evidence_level"] or 0), level)
            month["evidence_label"] = evidence_labels[int(month["evidence_level"])]
            month["events"].append({
                "event": row["event_name"],
                "event_name": row["event_name"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "affected_regions": row["impacted_us_regions"],
                "impacted_us_regions": row["impacted_us_regions"],
                "impacted_us_states": episode["impacted_us_states"],
                "source_fires": row["source_fire_names"],
                "source_fire_names": row["source_fire_names"],
                "source_title": primary_source["title"],
                "source_url": primary_source["url"],
                "evidence_level": level,
                "evidence_label": evidence_labels[level],
                "attribution_confidence": row["attribution_confidence"],
                "pm25_metric": episode["pm25_metric"],
                "aqi_metric": episode["aqi_metric"],
            })
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)

    for row in stanford_daily_rows:
        day = date.fromisoformat(row["date"])
        month = history_by_year[day.year][day.month - 1]
        if month["status"] != "modeled_comparable":
            events = month["events"]
            month.update(empty_history_month("modeled_comparable"))
            month["events"] = events
            for field in ("observed_days", "smoke_days", "broad_days", "population_days", "peak_population_exposed"):
                month[field] = 0
        exposed_population = int(row["population_exposed_pm25_ge_35_5"])
        month["observed_days"] += 1
        month["smoke_days"] += int(exposed_population > 0)
        month["broad_days"] += int(row["broad_day_10m"])
        month["population_days"] += exposed_population
        month["peak_population_exposed"] = max(
            month["peak_population_exposed"], exposed_population
        )

    operational_daily_rows = rows(PROCESSED / "operational_smoke_proxy_daily_2024_2026.csv")
    for row in operational_daily_rows:
        day = date.fromisoformat(row["date"])
        month = history_by_year[day.year][day.month - 1]
        if month["status"] != "operational_proxy":
            events = month["events"]
            month.update(empty_history_month("operational_proxy"))
            month["events"] = events
            for field in ("observed_days", "smoke_days", "broad_days", "population_days", "peak_population_exposed"):
                month[field] = 0
        indicative_population = int(row["indicative_county_population"])
        month["observed_days"] += 1
        month["smoke_days"] += int(indicative_population > 0)
        month["broad_days"] += int(row["broad_proxy_day_10m"])
        month["population_days"] += indicative_population
        month["peak_population_exposed"] = max(
            month["peak_population_exposed"], indicative_population
        )

    for month in history_by_year[cutoff_year]:
        if month["status"] == "no_comparable_daily_data":
            month["status"] = "not_yet_observed"

    smoke_history = [{"year": year, "months": history_by_year[year]} for year in history_by_year]

    fire_history_lookup: dict[tuple[int, int], dict[str, dict]] = {}
    for row in rows(PROCESSED / "fire_incidents_monthly_source_covered.csv"):
        key = (int(row["year"]), int(row["month"]))
        geography_key = "united_states" if row["geography"] == "United States" else "canada"
        fire_history_lookup.setdefault(key, {})[geography_key] = {
            "record_count": int(row["record_count"]) if row["record_count"] else None,
            "burned_acres": int(row["burned_acres"]) if row["burned_acres"] else None,
            "named_record_count": int(row["named_record_count"]) if row["named_record_count"] else None,
            "records_with_coordinates": int(row["records_with_coordinates"]) if row["records_with_coordinates"] else None,
            "certified_or_final_count": int(row["certified_or_final_count"]) if row["certified_or_final_count"] else None,
            "source_id": row["source_id"] or None,
            "source_scope": row["source_scope"] or None,
            "coverage_tier": row["coverage_tier"],
            "coverage_status": row["coverage_status"],
            "calendar_window_complete": row["calendar_window_complete"] == "true",
            "provisional": row["provisional"] == "true",
        }
    fire_history = [{
        "year": year,
        "months": [{
            "united_states": fire_history_lookup[(year, month)]["united_states"],
            "canada": fire_history_lookup[(year, month)]["canada"],
        } for month in range(1, 13)],
    } for year in range(1950, cutoff_year + 1)]

    fire_incident_catalog = [{
        "year": int(row["year"]),
        "geography": row["geography"],
        "record_count": int(row["record_count"]) if row["record_count"] else None,
        "burned_acres": int(row["burned_acres"]) if row["burned_acres"] else None,
        "records_with_unknown_month": int(row["records_with_unknown_month"]),
        "source_id": row["source_id"] or None,
        "source_scope": row["source_scope"] or None,
        "coverage_tier": row["coverage_tier"],
        "coverage_status": row["coverage_status"],
        "provisional": row["provisional"] == "true",
    } for row in rows(PROCESSED / "fire_incidents_annual_catalog_1950_2026.csv")]

    annual_fire = [{
        "year": int(row["year"]),
        "fire_count": int(row["fire_count"]),
        "acres_burned": int(row["acres_burned"]),
        "provisional": int(row["year"]) >= 2025,
    } for row in rows(PROCESSED / "mtbs_wildfires_annual.csv")]

    annual_canada_fire = [{
        "year": int(row["year"]),
        "fire_count": None,
        "acres_burned": round(float(row["burned_area_acres"])),
        "provisional": row["complete"].lower() != "true",
    } for row in rows(PROCESSED / "canada_fire_annual.csv")]

    def decade_change(data: list[dict], first_period: str, recent_period: str) -> dict:
        first_average = round(sum(row["acres_burned"] for row in data[:10]) / 10)
        recent_average = round(sum(row["acres_burned"] for row in data[-10:]) / 10)
        return {
            "first_period": first_period,
            "recent_period": recent_period,
            "first_average_acres": first_average,
            "recent_average_acres": recent_average,
            "percent_change": round((recent_average / first_average - 1) * 100),
        }

    complete_us_fire = [row for row in annual_fire if row["year"] <= 2024]
    fire_trends = {
        "canada": decade_change(annual_canada_fire, "1972–1981", "2016–2025"),
        "united_states": decade_change(complete_us_fire, "1984–1993", "2015–2024"),
    }

    operational_proxy = [{
        "year": int(row["year"]),
        "status": row["status"],
        "as_of_date": row["as_of_date"],
        "broad_proxy_days": int(row["broad_proxy_days_10m"]),
        "indicative_population_days": int(row["indicative_county_population_days"]),
        "peak_indicative_population": int(row["peak_indicative_county_population"]),
        "peak_date": row["peak_date"],
        "monitor_site_days": int(row["smoke_coincident_high_pm25_monitor_site_days"]),
        "qualifying_county_days": int(row["smoke_coincident_high_pm25_county_days"]),
        "monitored_counties": int(row["monitored_counties"]),
        "qualifying_counties": int(row["qualifying_counties"]),
    } for row in rows(PROCESSED / "operational_smoke_proxy_annual_2024_2026.csv")]

    operational_same_cutoff = []
    cutoff_month_day = operational_proxy[-1]["as_of_date"][5:]
    for year in sorted({int(row["year"]) for row in operational_daily_rows}):
        cutoff_rows = [
            row for row in operational_daily_rows
            if int(row["year"]) == year and row["date"][5:] <= cutoff_month_day
        ]
        peak_row = max(cutoff_rows, key=lambda row: int(row["indicative_county_population"]))
        operational_same_cutoff.append({
            "year": year,
            "cutoff": f"{year}-{cutoff_month_day}",
            "days_in_window": len(cutoff_rows),
            "broad_proxy_days": sum(int(row["broad_proxy_day_10m"]) for row in cutoff_rows),
            "indicative_population_days": sum(
                int(row["indicative_county_population"]) for row in cutoff_rows
            ),
            "peak_indicative_population": int(peak_row["indicative_county_population"]),
            "peak_date": peak_row["date"],
        })

    smoke_same_cutoff = []
    for year in sorted({int(row["year"]) for row in stanford_daily_rows}):
        cutoff_rows = [
            row for row in stanford_daily_rows
            if int(row["year"]) == year and row["date"][5:] <= cutoff_month_day
        ]
        peak_row = max(
            cutoff_rows,
            key=lambda row: int(row["population_exposed_pm25_ge_35_5"]),
        )
        smoke_same_cutoff.append({
            "year": year,
            "cutoff": f"{year}-{cutoff_month_day}",
            "series_kind": "stanford_modeled",
            "series_label": "Stanford modeled smoke PM2.5",
            "comparable_to_2026": False,
            "days_in_window": len(cutoff_rows),
            "broad_days": sum(int(row["broad_day_10m"]) for row in cutoff_rows),
            "population_days": sum(
                int(row["population_exposed_pm25_ge_35_5"]) for row in cutoff_rows
            ),
            "peak_population": int(peak_row["population_exposed_pm25_ge_35_5"]),
            "peak_date": peak_row["date"],
        })
    operational_screen_same_cutoff = rows(
        PROCESSED / "operational_smoke_screen_same_cutoff_2006_2026.csv"
    )
    smoke_same_cutoff.extend({
        "year": int(row["year"]),
        "cutoff": row["window_end"],
        "series_kind": "operational_proxy",
        "series_label": (
            "Final EPA AQS + NOAA HMS observed screen"
            if row["monitor_source_tier"] == "final_aqs_daily"
            else "EPA AQS/AirNow + NOAA HMS observed screen"
        ),
        "comparable_to_2026": True,
        "identical_monitor_source_to_2026": row["identical_monitor_source_to_2026"] == "true",
        "days_in_window": int(row["calendar_days_in_scope"]),
        "broad_days": int(row["broad_proxy_days_10m"]),
        "population_days": int(row["indicative_county_population_days"]),
        "peak_population": int(row["peak_indicative_county_population"]),
        "peak_date": row["peak_date"],
        "monitor_source_tier": row["monitor_source_tier"],
        "balanced_panel_population_days": int(
            row["balanced_panel_indicative_county_population_days"]
        ),
        "balanced_panel_broad_days": int(row["balanced_panel_broad_proxy_days_10m"]),
        "balanced_panel_sites": int(row["balanced_panel_sites_defined"]),
    } for row in operational_screen_same_cutoff)

    fire_density_source = rows(PROCESSED / "all_fire_density_tiles_1992_2020.csv")
    burned_acres_values = sorted(int(row["burned_acres"]) for row in fire_density_source)

    def interpolated_quantile(values: list[int], probability: float) -> int:
        position = (len(values) - 1) * probability
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        fraction = position - lower
        return round(values[lower] * (1 - fraction) + values[upper] * fraction)

    density_probabilities = (0.10, 0.25, 0.50, 0.75, 0.90)
    density_thresholds = [
        interpolated_quantile(burned_acres_values, probability)
        for probability in density_probabilities
    ]
    top_decile_values = [
        acres for acres in burned_acres_values if acres > density_thresholds[-1]
    ]
    density_total_acres = sum(burned_acres_values)
    top_decile_share = round(
        sum(top_decile_values) / density_total_acres * 100,
        1,
    )
    fire_density_scale = {
        "method": "distribution_quantiles",
        "metric": "reported_burned_acres_per_grid_cell",
        "probabilities": list(density_probabilities),
        "thresholds": density_thresholds,
        "top_decile_cell_count": len(top_decile_values),
        "top_decile_share_percent": top_decile_share,
    }
    fire_density_tiles = []
    for row in fire_density_source:
        regions = [region for region in row["regions"].split("; ") if region]
        us_fire_count = int(row["us_fire_count"])
        canada_fire_count = int(row["canada_fire_count"])
        fire_density_tiles.append({
            "x": int(row["x"]),
            "y": int(row["y"]),
            "year_start": int(row["year_start"]),
            "year_end": int(row["year_end"]),
            "fire_count": int(row["fire_count"]),
            "burned_acres": int(row["burned_acres"]),
            "us_fire_count": us_fire_count,
            "canada_fire_count": canada_fire_count,
            "level": sum(
                int(row["burned_acres"]) > threshold
                for threshold in density_thresholds
            ),
            "geographies": [
                geography for geography, count in (
                    ("United States", us_fire_count), ("Canada", canada_fire_count)
                ) if count
            ],
            "label": ", ".join(regions[:3]) + (" + more" if len(regions) > 3 else ""),
            "source_ids": row["source_ids"].split(";"),
            "coverage_note": row["coverage_note"],
        })
    fire_density_tiles.sort(key=lambda row: (row["y"], row["x"]))

    current_fire_activity = [{
        "year": int(row["year"]),
        "geography": row["geography"],
        "fire_count": int(row["fire_count"]),
        "burned_area_hectares": (
            round(float(row["burned_area_ha"]), 1) if row["burned_area_ha"] else None
        ),
        "burned_area_acres": int(row["burned_area_acres"]),
        "as_of_date": row["as_of_date"],
        "status": row["status"],
        "complete": row["complete"].lower() == "true",
        "comparable_to_historical_complete_series": (
            row["comparable_to_historical_complete_series"].lower() == "true"
        ),
        "source_dataset": row["source_dataset"],
        "source_url": row["source_url"],
    } for row in rows(PROCESSED / "current_fire_activity_2026.csv")]

    fire_year_context = [{
        "year": int(row["year"]),
        "geography": row["geography"],
        "rank": int(row["rank"]),
        "fire_name": row["fire_name"],
        "label_kind": row["label_kind"],
        "region": row["region"],
        "acres": int(row["acres"]),
        "source_dataset": row["source_dataset"],
        "provisional": row["provisional"].lower() == "true",
        "causal_smoke_attribution": row["causal_smoke_attribution"].lower() == "true",
    } for row in rows(PROCESSED / "fire_year_context.csv")]

    smoke_region_context = [{
        "year": int(row["year"]),
        "rank": int(row["rank"]),
        "state_fips": row["state_fips"],
        "state": row["state"],
        "high_smoke_population_days": int(row["high_smoke_population_days"]),
        "high_smoke_days": int(row["high_smoke_days"]),
        "peak_population_exposed": int(row["peak_population_exposed"]),
        "model_id": row["model_id"],
    } for row in rows(PROCESSED / "smoke_region_context_2006_2023.csv")]

    regional_shift = {
        "top_state_by_year": [
            {
                "year": row["year"],
                "state": row["state"],
                "state_fips": row["state_fips"],
            }
            for row in smoke_region_context if row["rank"] == 1
        ],
        "top5_2023": {
            "states": [
                row["state"] for row in smoke_region_context
                if row["year"] == 2023 and row["rank"] <= 5
            ],
            "share_percent": round(
                sum(
                    row["high_smoke_population_days"] for row in smoke_region_context
                    if row["year"] == 2023 and row["rank"] <= 5
                )
                / next(row["population_days"] for row in annual_smoke if row["year"] == 2023)
                * 100
            ),
        },
    }

    us_2023 = next(row for row in annual_fire if row["year"] == 2023)
    canada_2023 = next(row for row in annual_canada_fire if row["year"] == 2023)
    us_baseline = round(
        sum(row["acres_burned"] for row in annual_fire if 2013 <= row["year"] <= 2022)
        / 10
    )
    canada_baseline = round(
        sum(
            row["acres_burned"] for row in annual_canada_fire
            if 2013 <= row["year"] <= 2022
        ) / 10
    )
    smoke_2023 = next(row for row in annual_smoke if row["year"] == 2023)
    fire_smoke_decoupling = {
        "year": 2023,
        "us_mtbs_acres": us_2023["acres_burned"],
        "us_mtbs_2013_2022_average_acres": us_baseline,
        "us_change_vs_average_percent": round(
            (us_2023["acres_burned"] / us_baseline - 1) * 100
        ),
        "canada_nbac_acres": canada_2023["acres_burned"],
        "canada_nbac_2013_2022_average_acres": canada_baseline,
        "canada_multiple_of_average": round(
            canada_2023["acres_burned"] / canada_baseline,
            1,
        ),
        "us_smoke_population_days": smoke_2023["population_days"],
        "us_smoke_rank": smoke_2023["burden_rank"],
    }

    manifest = json.loads(MANIFEST.read_text())
    sources = [{
        "id": source["id"], "title": source["title"], "organization": source["organization"],
        "url": source["url"], "retrieval_url": source.get("retrieval_url"),
        "coverage": source["coverage"], "role": source["role"],
        "license": source.get("license"), "grain": source.get("grain"),
        "comparable": source["comparable"],
    } for source in manifest["sources"]]

    dashboard = {
        "meta": {
            "title": "Wildfire smoke exposure and fire context",
            "generated_at": current_receipt["retrieved_at"],
            "publication_cutoff_date": publication_cutoff,
            "smoke_series_start_year": 2006,
            "smoke_series_end_year": 2023,
            "operational_proxy_start_year": 2024,
            "operational_proxy_end_year": 2026,
            "operational_screen_start_year": 2006,
            "operational_screen_end_year": 2026,
            "operational_proxy_as_of_date": operational_proxy[-1]["as_of_date"],
            "same_cutoff_month_day": cutoff_month_day,
            "fire_density_geometry_version": "na-equirectangular-30x24-v1",
            "fire_density_period": "1992–2020",
            "fire_series_start_year": 1984,
            "fire_series_end_year": 2026,
            "canada_fire_series_start_year": 1972,
            "canada_fire_series_end_year": 2025,
            "provisional_years": [2025, 2026],
            "notes": [
                "annual_smoke uses Stanford ECHO county-day estimates and fixed July 1, 2020 county populations.",
                "population_days and peak_population_exposed are people-based counts, not millions.",
                "smoke_days means HMS-overhead days when PM2.5 minus the released seasonal median no-smoke background reached 35.5 µg/m³, the AQI-101 concentration breakpoint.",
                "Actual AQI is based on total PM2.5; the site describes this as an AQI-101-equivalent wildfire-smoke increment, never a literal wildfire AQI.",
                f"Share and per-capita figures divide by the fixed July 1, 2020 CONUS+DC county population of {fixed_population:,}; they describe residence, not daily location.",
                "A widespread smoke day is a date when counties containing at least 10 million fixed residents cross the AQI-101-equivalent wildfire-smoke threshold at once.",
                "MTBS covers large mapped U.S. fires and excludes Canadian fires; 2025-2026 records are incomplete and provisional.",
                "Canadian NBAC burned area is a separate 1972-2025 complete annual series; comparable national fire counts are not available in that product.",
                "Pre-2006 episodes are documented context, not observations comparable to the modeled 2006-2023 series.",
                f"The 2024-2026 operational proxy counts total-PM2.5 monitor observations at or above 35.5 ug/m3 under NOAA HMS smoke polygons. The {cutoff_year} row is a provisional AQS/AirNow composite through {publication_cutoff}. County population is an indicative scale, not a Stanford-equivalent exposure estimate.",
                f"current_fire_activity is a separate {publication_cutoff} YTD snapshot from NIFC and NRCan CWFIF. It must not be spliced into complete MTBS or NBAC annual histories."
            ]
        },
        "annual_smoke": annual_smoke,
        "smoke_trend": smoke_trend,
        "extremes": extremes,
        "seasonality": seasonality,
        "regional_shift": regional_shift,
        "fire_smoke_decoupling": fire_smoke_decoupling,
        "smoke_history": smoke_history,
        "fire_history": fire_history,
        "fire_incident_catalog": fire_incident_catalog,
        "operational_proxy": operational_proxy,
        "operational_same_cutoff": operational_same_cutoff,
        "smoke_same_cutoff": smoke_same_cutoff,
        "current_fire_activity": current_fire_activity,
        "fire_year_context": fire_year_context,
        "smoke_region_context": smoke_region_context,
        "documented_smoke_episodes": documented_smoke_episodes,
        "annual_fire": annual_fire,
        "annual_canada_fire": annual_canada_fire,
        "fire_trends": fire_trends,
        "fire_density_scale": fire_density_scale,
        "fire_density_tiles": fire_density_tiles,
        "sources": sources,
        "research_papers": manifest["research_papers"],
    }
    out = PROCESSED / "dashboard.json"
    out.write_text(json.dumps(dashboard, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"wrote {out} with {len(fire_year_context):,} annual fire-context records")


if __name__ == "__main__":
    main()
