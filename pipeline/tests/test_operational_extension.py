"""Contract, event-policy and geometry tests for the AQS/HMS smoke screen."""

from __future__ import annotations

import csv
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from pipeline.process_operational_extension import (
    BALANCED_PANEL_MIN_COVERAGE,
    PM25_THRESHOLD,
    load_aqs_year,
    ring_contains,
)


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def rows(name: str) -> list[dict[str, str]]:
    with (PROCESSED / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class OperationalExtensionTests(unittest.TestCase):
    def test_aqi_101_threshold_and_polygon_boundary(self) -> None:
        self.assertEqual(PM25_THRESHOLD, 35.5)
        square = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]
        self.assertTrue(ring_contains(0.0, 0.0, square))
        self.assertFalse(ring_contains(2.0, 0.0, square))

    def test_event_included_variant_is_kept_and_excluded_variant_is_ignored(self) -> None:
        fieldnames = [
            "State Code", "County Code", "Site Num", "Date Local", "Observation Percent",
            "Arithmetic Mean", "Latitude", "Longitude", "Event Type",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            for parameter in (88101, 88502):
                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()
                if parameter == 88101:
                    writer.writerows([
                        {
                            "State Code": "06", "County Code": "001", "Site Num": "0001",
                            "Date Local": "2024-01-01", "Observation Percent": "100",
                            "Arithmetic Mean": "44", "Latitude": "37", "Longitude": "-122",
                            "Event Type": "Included",
                        },
                        {
                            "State Code": "06", "County Code": "001", "Site Num": "0001",
                            "Date Local": "2024-01-01", "Observation Percent": "100",
                            "Arithmetic Mean": "9", "Latitude": "37", "Longitude": "-122",
                            "Event Type": "Excluded",
                        },
                    ])
                with zipfile.ZipFile(directory / f"daily_{parameter}_2024.zip", "w") as archive:
                    archive.writestr(f"daily_{parameter}_2024.csv", buffer.getvalue())
            monitor_days, audit = load_aqs_year(2024, directory)
        selected = monitor_days[("2024-01-01", "060010001")]
        self.assertEqual(selected["pm25"], 44.0)
        self.assertTrue(selected["event_included"])
        self.assertEqual(audit.event_excluded_rows_ignored, 1)
        self.assertEqual(audit.event_excluded_only_site_days, 0)

    def test_daily_and_annual_complete_screen_contract(self) -> None:
        daily = rows("operational_smoke_screen_daily_2006_2026.csv")
        dates = [row["date"] for row in daily]
        self.assertEqual(len(dates), len(set(dates)))
        self.assertEqual((dates[0], dates[-1]), ("2006-01-01", "2026-07-18"))
        self.assertEqual(len([row for row in daily if row["year"] == "2024"]), 366)
        self.assertEqual(len([row for row in daily if row["year"] == "2025"]), 365)
        self.assertEqual(len([row for row in daily if row["year"] == "2026"]), 199)
        self.assertTrue(all(row["comparable_to_stanford"] == "false" for row in daily))
        for row in daily:
            self.assertLessEqual(
                int(row["smoke_coincident_high_pm25_monitor_sites"]),
                int(row["high_pm25_monitor_sites"]),
            )
            self.assertLessEqual(int(row["high_pm25_monitor_sites"]), int(row["valid_monitor_sites"]))
            self.assertLessEqual(
                int(row["balanced_smoke_coincident_high_pm25_monitor_sites"]),
                int(row["smoke_coincident_high_pm25_monitor_sites"]),
            )
            self.assertLessEqual(
                int(row["balanced_indicative_county_population"]),
                int(row["indicative_county_population"]),
            )

        annual = rows("operational_smoke_screen_annual_2006_2026.csv")
        self.assertEqual([int(row["year"]) for row in annual], list(range(2006, 2027)))
        self.assertTrue(all(row["status"] == "calendar_year_snapshot_revisionable" for row in annual[:-1]))
        self.assertEqual(annual[-1]["status"], "year_to_date_composite_snapshot")
        self.assertEqual(annual[-1]["as_of_date"], "2026-07-18")
        self.assertEqual(annual[-1]["aqs_data_through"], "2026-05-31")
        self.assertEqual(annual[-1]["airnow_supplement_start"], "2026-06-01")
        row_2014 = next(row for row in annual if row["year"] == "2014")
        self.assertEqual(row_2014["hms_data_through"], "2014-12-31")
        self.assertEqual(row_2014["hms_last_polygon_date"], "2014-12-30")
        for row in annual:
            year_daily = [item for item in daily if item["year"] == row["year"]]
            self.assertEqual(
                sum(int(item["indicative_county_population"]) for item in year_daily),
                int(row["indicative_county_population_days"]),
            )
            self.assertEqual(
                sum(int(item["broad_proxy_day_10m"]) for item in year_daily),
                int(row["broad_proxy_days_10m"]),
            )

    def test_fixed_window_has_every_year_and_same_number_of_days(self) -> None:
        fixed = rows("operational_smoke_screen_same_cutoff_2006_2026.csv")
        self.assertEqual([int(row["year"]) for row in fixed], list(range(2006, 2027)))
        expected_days = {
            2008: 200,
            2012: 200,
            2016: 200,
            2020: 200,
            2024: 200,
        }
        for row in fixed:
            year = int(row["year"])
            self.assertEqual(int(row["calendar_days_in_scope"]), expected_days.get(year, 199))
            self.assertEqual(row["window_end"], f"{year}-07-18")
            self.assertEqual(row["comparable_to_stanford"], "false")
        self.assertEqual(fixed[-1]["identical_monitor_source_to_2026"], "true")
        self.assertTrue(all(row["identical_monitor_source_to_2026"] == "false" for row in fixed[:-1]))

    def test_coverage_and_balanced_panel_are_explicit(self) -> None:
        coverage = rows("operational_smoke_screen_monitor_coverage_2006_2026.csv")
        self.assertEqual(len(coverage), 21)
        panel_sizes = {int(row["balanced_panel_sites_defined"]) for row in coverage}
        self.assertEqual(len(panel_sizes), 1)
        self.assertGreater(next(iter(panel_sizes)), 0)
        self.assertEqual(BALANCED_PANEL_MIN_COVERAGE, 0.75)
        for row in coverage:
            self.assertGreater(int(row["days_with_any_valid_site"]), 0)
            self.assertGreater(int(row["distinct_monitored_states_dc"]), 0)
            self.assertGreater(float(row["monitored_county_population_share_pct"]), 0)

    def test_legacy_current_files_reconcile_to_complete_screen(self) -> None:
        complete_daily = [
            row for row in rows("operational_smoke_screen_daily_2006_2026.csv")
            if int(row["year"]) >= 2024
        ]
        complete_annual = [
            row for row in rows("operational_smoke_screen_annual_2006_2026.csv")
            if int(row["year"]) >= 2024
        ]
        self.assertEqual(rows("operational_smoke_proxy_daily_2024_2026.csv"), complete_daily)
        self.assertEqual(rows("operational_smoke_proxy_annual_2024_2026.csv"), complete_annual)


if __name__ == "__main__":
    unittest.main()
