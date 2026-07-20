import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def rows(name):
    with (PROCESSED / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class PipelineOutputTests(unittest.TestCase):
    def test_zcta_dimension_grain_and_state(self):
        data = rows("zcta_2020.csv")
        self.assertEqual(len(data), 32923)
        self.assertEqual(len({row["zcta"] for row in data}), len(data))
        self.assertTrue(all(len(row["zcta"]) == 5 for row in data))
        self.assertTrue(all(row["state"] for row in data))

    def test_smoke_is_conus_and_reconciles_to_daily(self):
        localities = rows("zcta_smoke_exposure_2021.csv")
        self.assertEqual(len(localities), 32462)
        states = {row["state"] for row in localities}
        self.assertIn("DC", states)
        self.assertTrue(states.isdisjoint({"AK", "HI", "PR"}))
        daily = rows("zcta_smoke_daily_national_2021.csv")
        annual = rows("smoke_annual_2021.csv")[0]
        self.assertEqual(len(daily), 365)
        self.assertEqual(sum(int(row["population_exposed"]) for row in daily), int(annual["population_days"]))
        self.assertEqual(sum(int(row["broad_smoke_day"]) for row in daily), int(annual["broad_smoke_days"]))
        self.assertEqual(int(annual["broad_smoke_days"]), 4)

    def test_grid_distance_diagnostics(self):
        distances = sorted(float(row["grid_distance_km"]) for row in rows("zcta_smoke_exposure_2021.csv"))
        self.assertLessEqual(distances[int(0.99 * len(distances))], 11)
        self.assertEqual(sum(value > 20 for value in distances), 16)
        self.assertLess(max(distances), 55)

    def test_mtbs_wildfire_filter_and_units(self):
        data = rows("mtbs_wildfires_annual.csv")
        self.assertEqual((int(data[0]["year"]), int(data[-1]["year"])), (1984, 2026))
        self.assertEqual(sum(int(row["fire_count"]) for row in data), 16633)
        self.assertEqual(sum(int(row["acres_burned"]) for row in data), 179298695)

    def test_dashboard_contract_and_units(self):
        dashboard = json.loads((PROCESSED / "dashboard.json").read_text())
        self.assertEqual(dashboard["meta"]["smoke_series_end_year"], 2023)
        self.assertEqual(dashboard["meta"]["smoke_series_start_year"], 2006)
        self.assertEqual(dashboard["meta"]["operational_proxy_end_year"], 2026)
        self.assertEqual(dashboard["meta"]["operational_proxy_as_of_date"], "2026-07-18")
        self.assertEqual(dashboard["meta"]["publication_cutoff_date"], "2026-07-18")
        self.assertEqual(dashboard["meta"]["fire_series_start_year"], 1984)
        self.assertEqual(dashboard["meta"]["fire_series_end_year"], 2026)
        self.assertEqual(dashboard["meta"]["provisional_years"], [2025, 2026])
        self.assertEqual(len(dashboard["annual_smoke"]), 18)
        self.assertEqual(
            [row["year"] for row in dashboard["smoke_history"]],
            list(range(1950, 2027)),
        )
        self.assertTrue(all(len(row["months"]) == 12 for row in dashboard["smoke_history"]))
        self.assertEqual(len(dashboard["fire_incident_catalog"]), 154)
        fire_catalog = {
            (row["year"], row["geography"]): row
            for row in dashboard["fire_incident_catalog"]
        }
        self.assertIsNone(fire_catalog[(1950, "United States")]["record_count"])
        self.assertGreater(fire_catalog[(1950, "Canada")]["record_count"], 0)
        self.assertEqual(fire_catalog[(2026, "United States")]["provisional"], True)
        annual_by_year = {row["year"]: row for row in dashboard["annual_smoke"]}
        self.assertEqual(annual_by_year[2023]["share_exposed_at_least_once"], 47.4)
        self.assertEqual(annual_by_year[2023]["counties_exposed_at_least_once"], 1646)
        self.assertEqual(annual_by_year[2023]["per_capita_smoke_days"], 1.64)
        self.assertEqual(annual_by_year[2023]["severe_days_10m"], 7)
        self.assertEqual(annual_by_year[2023]["burden_rank"], 1)
        self.assertEqual(dashboard["smoke_trend"]["early_per_capita_days"], 0.08)
        self.assertEqual(dashboard["smoke_trend"]["recent_per_capita_days"], 0.76)
        self.assertEqual(dashboard["smoke_trend"]["cumulative_population_days"], 1879266000)
        self.assertEqual(dashboard["smoke_trend"]["cumulative_share_since_2019"], 66)
        self.assertEqual(dashboard["smoke_trend"]["cumulative_share_since_2017"], 86)
        self.assertEqual(len(dashboard["smoke_trend"]["rolling_mean_5yr"]), 14)
        self.assertEqual(dashboard["extremes"]["benchmark_day"]["population_exposed"], 11031060)
        self.assertEqual(dashboard["extremes"]["days_exceeding_benchmark_since_2016"], 36)
        self.assertEqual(dashboard["extremes"]["record_years"], [2008, 2017, 2018, 2020, 2023])
        worst_day = dashboard["extremes"]["top_days"][0]
        self.assertEqual(worst_day["date"], "2023-06-29")
        self.assertEqual(worst_day["population_exposed"], 88472845)
        self.assertEqual(worst_day["share_of_population"], 27.0)
        longest_streak = dashboard["extremes"]["longest_streaks"][0]
        self.assertEqual(longest_streak["start_date"], "2020-09-10")
        self.assertEqual(longest_streak["days"], 8)
        notable_2023 = next(row for row in dashboard["seasonality"]["notable_years"] if row["year"] == 2023)
        self.assertEqual(notable_2023["share_percent"], 84.9)
        self.assertEqual(dashboard["regional_shift"]["top5_2023"]["share_percent"], 52)
        self.assertEqual(dashboard["fire_smoke_decoupling"]["us_change_vs_average_percent"], -69)
        self.assertEqual(dashboard["fire_smoke_decoupling"]["canada_multiple_of_average"], 6.1)
        fixed_population = dashboard["smoke_trend"]["fixed_population"]
        self.assertEqual(
            sum(row["population_days"] for row in dashboard["annual_smoke"]),
            dashboard["smoke_trend"]["cumulative_population_days"],
        )
        self.assertEqual(
            sorted(row["burden_rank"] for row in dashboard["annual_smoke"]),
            list(range(1, 19)),
        )
        self.assertTrue(
            all(
                abs(round(row["per_capita_smoke_days"] * fixed_population) - row["population_days"])
                <= fixed_population // 200
                for row in dashboard["annual_smoke"]
            )
        )
        annual_broad_days = {
            row["year"]: row["broad_smoke_days"] for row in dashboard["annual_smoke"]
        }
        for row in dashboard["smoke_history"]:
            if row["year"] not in annual_broad_days:
                continue
            self.assertEqual(
                sum(month["broad_days"] for month in row["months"]),
                annual_broad_days[row["year"]],
            )
        self.assertEqual(
            [row["broad_proxy_days"] for row in dashboard["operational_same_cutoff"]],
            [4, 4, 4],
        )
        same_cutoff_by_kind = {
            kind: [row for row in dashboard["smoke_same_cutoff"] if row["series_kind"] == kind]
            for kind in {row["series_kind"] for row in dashboard["smoke_same_cutoff"]}
        }
        self.assertEqual(
            [row["year"] for row in same_cutoff_by_kind["stanford_modeled"]],
            list(range(2006, 2024)),
        )
        self.assertEqual(
            [row["year"] for row in same_cutoff_by_kind["operational_proxy"]],
            list(range(2006, 2027)),
        )
        self.assertTrue(all(row["cutoff"].endswith("-07-18") for row in dashboard["smoke_same_cutoff"]))
        self.assertEqual(
            {row["series_kind"] for row in dashboard["smoke_same_cutoff"]},
            {"stanford_modeled", "operational_proxy"},
        )
        self.assertTrue(all(not row["comparable_to_2026"] for row in same_cutoff_by_kind["stanford_modeled"]))
        self.assertTrue(all(row["comparable_to_2026"] for row in same_cutoff_by_kind["operational_proxy"]))
        self.assertEqual(
            [row["year"] for row in same_cutoff_by_kind["operational_proxy"] if row["identical_monitor_source_to_2026"]],
            [2026],
        )
        self.assertEqual(dashboard["fire_trends"]["canada"]["percent_change"], 99)
        self.assertEqual(dashboard["fire_trends"]["united_states"]["percent_change"], 239)
        self.assertEqual([row["year"] for row in dashboard["operational_proxy"]], [2024, 2025, 2026])
        self.assertEqual(
            [row["geography"] for row in dashboard["current_fire_activity"]],
            ["United States", "Canada"],
        )
        self.assertNotIn("localities", dashboard)
        self.assertNotIn("historical_episodes", dashboard)
        self.assertGreater(len(dashboard["fire_year_context"]), 300)
        self.assertGreater(len(dashboard["smoke_region_context"]), 200)
        self.assertTrue(all(isinstance(row["population_days"], int) for row in dashboard["annual_smoke"]))
        self.assertTrue(all(row["provisional"] == (row["year"] >= 2025) for row in dashboard["annual_fire"]))
        self.assertEqual(len(dashboard["annual_canada_fire"]), 54)
        self.assertEqual(
            (dashboard["annual_canada_fire"][0]["year"], dashboard["annual_canada_fire"][-1]["year"]),
            (1972, 2025),
        )
        self.assertGreater(len(dashboard["fire_density_tiles"]), 100)
        self.assertTrue(all(0 <= row["x"] < 30 and 0 <= row["y"] < 24 for row in dashboard["fire_density_tiles"]))
        self.assertTrue(all(0 <= row["level"] <= 5 for row in dashboard["fire_density_tiles"]))
        self.assertTrue(all(row["fire_count"] > 0 and row["burned_acres"] >= 0 for row in dashboard["fire_density_tiles"]))
        density_scale = dashboard["fire_density_scale"]
        self.assertEqual(density_scale["method"], "distribution_quantiles")
        self.assertEqual(density_scale["thresholds"], [3523, 45624, 461666, 1771064, 3477617])
        self.assertEqual(density_scale["top_decile_cell_count"], 29)
        self.assertEqual(density_scale["top_decile_share_percent"], 45.1)
        level_counts = [
            sum(row["level"] == level for row in dashboard["fire_density_tiles"])
            for level in range(6)
        ]
        self.assertTrue(all(count >= 25 for count in level_counts))

    def test_validation_overlap_is_explicit(self):
        report = json.loads((PROCESSED / "validation_report.json").read_text())
        self.assertEqual(report["status"], "PASS_FOR_2021_DEMO_WITH_LIMITATIONS")
        self.assertEqual(report["checks"]["conus_population_covered"], 328334009)
        self.assertEqual(report["checks"]["conus_dc_population_coverage_percent"], 99.72)
        comparison = report["stanford_2021_overlap"]
        self.assertEqual(comparison["broad_smoke_days"]["absolute_difference"], 1)
        self.assertAlmostEqual(comparison["population_days"]["percent_difference_vs_stanford"], 7.46)

    def test_processed_checksum_inventory(self):
        inventory = json.loads((ROOT / "data" / "processed_checksums.json").read_text())
        self.assertGreaterEqual(len(inventory["artifacts"]), 10)
        for artifact in inventory["artifacts"]:
            path = ROOT / artifact["path"]
            self.assertEqual(path.stat().st_size, artifact["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_operational_proxy_is_separate_and_reconciles_to_daily(self):
        annual = rows("operational_smoke_proxy_annual_2024_2026.csv")
        daily = rows("operational_smoke_proxy_daily_2024_2026.csv")
        self.assertEqual([int(row["year"]) for row in annual], [2024, 2025, 2026])
        self.assertTrue(all(row["comparable_to_stanford"] == "false" for row in annual))
        self.assertEqual(annual[-1]["status"], "year_to_date_composite_snapshot")
        self.assertEqual(annual[-1]["as_of_date"], "2026-07-18")
        for row in annual:
            year_rows = [item for item in daily if item["year"] == row["year"]]
            self.assertEqual(len(year_rows), int(row["calendar_days_in_scope"]))
            self.assertEqual(
                sum(int(item["broad_proxy_day_10m"]) for item in year_rows),
                int(row["broad_proxy_days_10m"]),
            )

    def test_current_fire_activity_is_ytd_and_not_spliced(self):
        data = rows("current_fire_activity_2026.csv")
        self.assertEqual(len(data), 2)
        by_geography = {row["geography"]: row for row in data}
        self.assertEqual(int(by_geography["United States"]["fire_count"]), 40357)
        self.assertEqual(int(by_geography["United States"]["burned_area_acres"]), 3853513)
        self.assertEqual(int(by_geography["Canada"]["fire_count"]), 3815)
        self.assertEqual(int(by_geography["Canada"]["burned_area_acres"]), 7202012)
        self.assertTrue(all(row["as_of_date"] == "2026-07-18" for row in data))
        self.assertTrue(all(row["complete"] == "false" for row in data))
        self.assertTrue(
            all(row["comparable_to_historical_complete_series"] == "false" for row in data)
        )

    def test_comprehensive_reported_fire_sources_remain_separate(self):
        annual = rows("all_fire_incidents_annual_source_covered.csv")
        by_geography = {}
        for row in annual:
            by_geography.setdefault(row["geography"], []).append(row)
        self.assertEqual(
            (int(by_geography["United States"][0]["year"]), int(by_geography["United States"][-1]["year"])),
            (1992, 2020),
        )
        self.assertEqual(
            (int(by_geography["Canada"][0]["year"]), int(by_geography["Canada"][-1]["year"])),
            (1950, 2025),
        )
        self.assertGreater(sum(int(row["fire_count"]) for row in by_geography["United States"]), 2_000_000)
        self.assertGreater(sum(int(row["fire_count"]) for row in by_geography["Canada"]), 400_000)
        self.assertTrue(all(row["comparable_to_other_geography"] == "false" for row in annual))

        tiles = rows("all_fire_density_tiles_1992_2020.csv")
        self.assertGreater(len(tiles), 250)
        self.assertTrue(all(0 <= int(row["x"]) < 30 and 0 <= int(row["y"]) < 24 for row in tiles))
        self.assertTrue(any(int(row["us_fire_count"]) and int(row["canada_fire_count"]) for row in tiles))


if __name__ == "__main__":
    unittest.main()
