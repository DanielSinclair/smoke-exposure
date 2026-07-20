import csv
import gzip
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def rows(name):
    with (PROCESSED / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class FireHistoryTests(unittest.TestCase):
    def test_monthly_catalog_has_complete_calendar_grain(self):
        data = rows("fire_incidents_monthly_source_covered.csv")
        self.assertEqual(len(data), 77 * 12 * 2)
        keys = {(row["geography"], row["year"], row["month"]) for row in data}
        self.assertEqual(len(keys), len(data))
        self.assertEqual({row["geography"] for row in data}, {"United States", "Canada"})
        self.assertTrue(all(row["comparable_over_time"] == "false" for row in data))
        self.assertTrue(all(row["causal_smoke_attribution"] == "false" for row in data))

    def test_missing_early_canadian_records_are_restored(self):
        data = rows("fire_incidents_monthly_source_covered.csv")
        early_canada = [
            row for row in data
            if row["geography"] == "Canada" and 1950 <= int(row["year"]) <= 1958
        ]
        self.assertEqual(sum(int(row["record_count"]) for row in early_canada), 15_001)
        self.assertEqual(
            {row["source_id"] for row in early_canada},
            {"nrcan-nfdb-all-fire-points-2026-06-08"},
        )

    def test_no_catalog_is_blank_not_zero(self):
        data = rows("fire_incidents_monthly_source_covered.csv")
        us_1950 = [row for row in data if row["geography"] == "United States" and row["year"] == "1950"]
        canada_2026 = [row for row in data if row["geography"] == "Canada" and row["year"] == "2026"]
        self.assertTrue(all(row["record_count"] == "" for row in us_1950 + canada_2026))
        self.assertTrue(all(row["coverage_status"] == "no_national_incident_catalog" for row in us_1950 + canada_2026[:7]))

    def test_monthly_and_unknown_months_reconcile_to_annual(self):
        monthly = rows("fire_incidents_monthly_source_covered.csv")
        annual = rows("fire_incidents_annual_catalog_1950_2026.csv")
        monthly_counts = {}
        for row in monthly:
            if row["record_count"] == "":
                continue
            key = (row["geography"], row["year"])
            monthly_counts[key] = monthly_counts.get(key, 0) + int(row["record_count"])
        for row in annual:
            if row["record_count"] == "":
                continue
            key = (row["geography"], row["year"])
            self.assertEqual(
                int(row["record_count"]),
                monthly_counts[key] + int(row["records_with_unknown_month"]),
            )

    def test_live_snapshot_receipt_matches_ignored_input(self):
        snapshot = ROOT / "sources/nifc-inform/2026-07-20/wildfire_records_2021_2026.ndjson.gz"
        receipt = json.loads((snapshot.parent / "receipt.json").read_text())
        self.assertEqual(snapshot.stat().st_size, receipt["bytes"])
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), receipt["sha256"])
        with gzip.open(snapshot, "rt", encoding="utf-8") as handle:
            self.assertEqual(sum(1 for _ in handle), receipt["record_count"])
        self.assertEqual(
            receipt["record_count"] + receipt["missing_object_id_count"],
            receipt["object_id_count"],
        )

    def test_dashboard_keeps_unavailable_smoke_metrics_null(self):
        dashboard = json.loads((PROCESSED / "dashboard.json").read_text())
        unavailable = [
            month
            for year in dashboard["smoke_history"]
            for month in year["months"]
            if month["status"] in {"no_comparable_daily_data", "not_yet_observed"}
        ]
        metric_fields = (
            "observed_days", "smoke_days", "broad_days",
            "population_days", "peak_population_exposed",
        )
        self.assertTrue(unavailable)
        self.assertTrue(all(month[field] is None for month in unavailable for field in metric_fields))
        self.assertEqual(len(dashboard["fire_history"]), 77)


if __name__ == "__main__":
    unittest.main()
