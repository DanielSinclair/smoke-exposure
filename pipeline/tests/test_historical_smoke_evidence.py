import csv
from datetime import date
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def rows(name):
    with (PROCESSED / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class HistoricalSmokeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = rows("historical_smoke_events_1950_2005.csv")
        cls.observations = rows("historical_smoke_observations_1950_2005.csv")
        cls.sources = rows("historical_smoke_sources.csv")
        cls.coverage = rows("historical_smoke_search_coverage_1950_2005.csv")
        cls.storm = rows("noaa_storm_events_wildfire_candidates_1950_2005.csv")

    def test_normalized_grains_are_unique_and_referentially_complete(self):
        self.assertEqual(len(self.events), len({row["event_id"] for row in self.events}))
        self.assertEqual(len(self.observations), len({row["observation_id"] for row in self.observations}))
        self.assertEqual(len(self.sources), len({row["source_id"] for row in self.sources}))
        event_ids = {row["event_id"] for row in self.events}
        source_ids = {row["source_id"] for row in self.sources}
        self.assertEqual(event_ids, {row["event_id"] for row in self.observations})
        self.assertTrue(all(row["source_id"] in source_ids for row in self.observations))
        self.assertTrue(all(
            set(row["primary_source_ids"].split("|")) <= source_ids for row in self.events
        ))

    def test_events_are_documentary_and_bounded(self):
        self.assertGreaterEqual(len(self.events), 15)
        for row in self.events:
            start, end = date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])
            self.assertLessEqual(start, end)
            self.assertGreaterEqual(start, date(1950, 1, 1))
            self.assertLessEqual(end, date(2005, 12, 31))
            self.assertEqual(row["quantitatively_comparable"], "false")
            self.assertIn(row["attribution_confidence"], {"confirmed", "probable", "possible", "unknown"})
            self.assertIn(int(row["evidence_level"]), range(1, 5))
            self.assertTrue(row["impacted_us_regions"])

    def test_search_ledger_has_every_month_without_false_zeroes(self):
        self.assertEqual(len(self.coverage), 56 * 12)
        keys = {(int(row["year"]), int(row["month"])) for row in self.coverage}
        self.assertEqual(keys, {(year, month) for year in range(1950, 2006) for month in range(1, 13)})
        self.assertTrue(all(row["quantitatively_comparable"] == "false" for row in self.coverage))
        self.assertTrue(all(row["absence_interpretation"] != "no_smoke" for row in self.coverage))
        empty = [row for row in self.coverage if int(row["documented_event_count"]) == 0]
        self.assertTrue(empty)
        self.assertTrue(all(
            row["absence_interpretation"] in {
                "unknown_not_zero", "no_qualifying_case_in_screened_sources_not_no_smoke"
            } for row in empty
        ))
        by_month = {(int(row["year"]), int(row["month"])): row for row in self.coverage}
        self.assertEqual(by_month[(1995, 7)]["review_status"], "not_systematically_reviewed")
        self.assertEqual(by_month[(1995, 7)]["absence_interpretation"], "unknown_not_zero")
        self.assertEqual(
            by_month[(1996, 7)]["review_status"],
            "candidate_screen_complete_not_exhaustive",
        )

    def test_event_months_reconcile_to_search_ledger(self):
        expected = {}
        for row in self.events:
            cursor = date.fromisoformat(row["start_date"])
            end = date.fromisoformat(row["end_date"])
            while cursor <= end:
                key = (cursor.year, cursor.month)
                expected[key] = expected.get(key, 0) + 1
                cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        actual = {
            (int(row["year"]), int(row["month"])): int(row["documented_event_count"])
            for row in self.coverage
        }
        for key, count in expected.items():
            self.assertEqual(actual[key], count)
        self.assertEqual(sum(actual.values()), sum(expected.values()))

    def test_noaa_storm_events_is_candidate_context_not_smoke_exposure(self):
        self.assertEqual(len(self.storm), 2236)
        self.assertEqual(len(self.storm), len({row["storm_event_id"] for row in self.storm}))
        self.assertEqual({int(row["year"]) for row in self.storm}, set(range(1996, 2006)))
        self.assertTrue(all(row["event_type"] == "Wildfire" for row in self.storm))
        self.assertTrue(all(row["role"] == "incident_candidate_or_corroboration_only" for row in self.storm))
        self.assertTrue(all(row["quantitatively_comparable"] == "false" for row in self.storm))
        self.assertGreater(sum(row["narrative_smoke_signal"] == "true" for row in self.storm), 0)
        self.assertTrue(all(
            date.fromisoformat(row["start_date"]) <= date.fromisoformat(row["end_date"])
            for row in self.storm
        ))
        receipt = json.loads(
            (ROOT / "sources/noaa-storm-events/1950-2005/receipt.json").read_text()
        )
        receipt_names = {Path(record["local_path"]).name for record in receipt["files"]}
        self.assertTrue({row["source_file"] for row in self.storm} <= receipt_names)


if __name__ == "__main__":
    unittest.main()
