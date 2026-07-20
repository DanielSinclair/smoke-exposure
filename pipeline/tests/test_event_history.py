import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def rows(name):
    with (PROCESSED / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class EventHistoryTests(unittest.TestCase):
    def test_normalized_large_fire_dataset_has_unique_stable_grain(self):
        data = rows("large_fire_incidents_source_covered.csv")
        self.assertGreater(len(data), 30_000)
        self.assertEqual(len(data), len({row["normalized_record_id"] for row in data}))
        self.assertEqual({row["geography"] for row in data}, {"United States", "Canada"})
        self.assertTrue(all(row["causal_smoke_attribution"] == "false" for row in data))
        self.assertTrue(all(int(row["acres"]) >= 0 for row in data))
        self.assertTrue(all(row["source_year_status"] for row in data))
        self.assertTrue(all(row["coverage_scope"] for row in data))
        self.assertTrue(all(row["source_coverage_complete"] == "false" for row in data if row["geography"] == "Canada"))

    def test_normalized_us_records_reconcile_to_mtbs_annual_output(self):
        data = rows("large_fire_incidents_source_covered.csv")
        normalized = {}
        for row in data:
            if row["geography"] != "United States":
                continue
            year = int(row["year"])
            summary = normalized.setdefault(year, {"count": 0, "acres": 0})
            summary["count"] += 1
            summary["acres"] += int(row["acres"])
        mtbs = rows("mtbs_wildfires_annual.csv")
        self.assertEqual(sorted(normalized), [int(row["year"]) for row in mtbs])
        for row in mtbs:
            summary = normalized[int(row["year"])]
            self.assertEqual(summary["count"], int(row["fire_count"]))
            self.assertEqual(summary["acres"], int(row["acres_burned"]))

    def test_annual_source_covered_rollup_reconciles_to_records(self):
        data = rows("large_fire_incidents_source_covered.csv")
        expected = {}
        for row in data:
            key = (row["year"], row["geography"])
            summary = expected.setdefault(key, {"count": 0, "acres": 0})
            summary["count"] += 1
            summary["acres"] += int(row["acres"])
        rollup = rows("large_fire_incidents_annual_source_covered.csv")
        self.assertEqual(len(rollup), len(expected))
        for row in rollup:
            summary = expected[(row["year"], row["geography"])]
            self.assertEqual(int(row["incident_records"]), summary["count"])
            self.assertEqual(int(row["acres"]), summary["acres"])
            self.assertEqual(row["comparable_to_other_geography"], "false")

    def test_documented_episodes_are_data_driven_and_incomparable(self):
        data = rows("documented_smoke_episodes_1950_2005.csv")
        self.assertGreaterEqual(len(data), 15)
        self.assertEqual(len(data), len({row["event_id"] for row in data}))
        self.assertEqual(min(row["start_date"][:4] for row in data), "1950")
        self.assertEqual(max(row["start_date"][:4] for row in data), "2005")
        self.assertTrue({"1988", "1998", "2000", "2001", "2002", "2003", "2004", "2005"} <= {
            row["start_date"][:4] for row in data
        })
        self.assertTrue(all(row["quantitatively_comparable"] == "false" for row in data))
        self.assertTrue(all(row["source_url"].startswith("https://") for row in data))
        self.assertTrue(all(1 <= int(row["evidence_level"]) <= 4 for row in data))
        self.assertTrue(all(row["attribution_confidence"] in {"confirmed", "probable", "possible", "unknown"} for row in data))

    def test_fire_context_never_claims_smoke_attribution(self):
        data = rows("fire_year_context.csv")
        full = {
            row["normalized_record_id"]: row
            for row in rows("large_fire_incidents_source_covered.csv")
        }
        self.assertTrue(data)
        self.assertTrue(all(row["causal_smoke_attribution"] == "false" for row in data))
        self.assertTrue({row["geography"] for row in data} >= {"United States", "Canada"})
        self.assertTrue(all(1 <= int(row["rank"]) <= 3 for row in data))
        self.assertTrue(all(int(row["acres"]) >= 0 for row in data))
        self.assertGreaterEqual(min(int(row["year"]) for row in data), 1950)
        self.assertTrue(all(row["source_record_id"] for row in data))
        self.assertTrue(all(-90 <= float(row["latitude"]) <= 90 for row in data))
        self.assertTrue(all(-180 <= float(row["longitude"]) <= 180 for row in data))
        for row in data:
            source = full[row["normalized_record_id"]]
            self.assertEqual(row["year"], source["year"])
            self.assertEqual(row["geography"], source["geography"])
            self.assertEqual(row["region"], source["region"])
            self.assertEqual(row["acres"], source["acres"])
            self.assertEqual(row["fire_name"], source["incident_name"])

    def test_smoke_regions_match_comparable_years(self):
        data = rows("smoke_region_context_2006_2023.csv")
        self.assertEqual(sorted({int(row["year"]) for row in data}), list(range(2006, 2024)))
        by_year = {year: [] for year in range(2006, 2024)}
        for row in data:
            by_year[int(row["year"])].append(row)
        self.assertTrue(all(items for items in by_year.values()))
        self.assertTrue(all(
            sorted(int(row["rank"]) for row in items) == list(range(1, len(items) + 1))
            for items in by_year.values()
        ))
        self.assertTrue(all(row["model_id"].startswith("STANFORD_ECHO_V2") for row in data))

    def test_state_population_days_reconcile_to_national_annual_totals(self):
        regions = rows("smoke_region_context_2006_2023.csv")
        annual = rows("stanford_annual_smoke_2006_2023.csv")
        region_totals = {}
        for row in regions:
            year = int(row["year"])
            region_totals[year] = region_totals.get(year, 0) + int(row["high_smoke_population_days"])
        for row in annual:
            expected = round(float(row["population_days_aqi101plus_millions"]) * 1_000_000)
            self.assertLessEqual(abs(region_totals[int(row["year"])] - expected), 500)


if __name__ == "__main__":
    unittest.main()
