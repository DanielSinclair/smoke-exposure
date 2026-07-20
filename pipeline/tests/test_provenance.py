#!/usr/bin/env python3
"""Source-manifest integrity and local snapshot checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "sources" / "manifest.json"


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.sources = cls.manifest["sources"]

    def test_source_ids_are_unique_and_dashboard_records_are_traceable(self) -> None:
        ids = [source["id"] for source in self.sources]
        self.assertEqual(len(ids), len(set(ids)))
        for source in self.sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertTrue(source["coverage"])
            self.assertTrue(source["role"])
            self.assertIsInstance(source["comparable"], bool)

    def test_research_papers_have_stable_citations_and_links(self) -> None:
        papers = self.manifest["research_papers"]
        ids = [paper["id"] for paper in papers]
        self.assertEqual(len(papers), 8)
        self.assertEqual(len(ids), len(set(ids)))
        for paper in papers:
            self.assertTrue(paper["url"].startswith("https://"))
            self.assertTrue(paper["citation"])
            self.assertTrue(paper["role"])
            if "download_url" in paper:
                self.assertTrue(paper["download_url"].startswith("https://"))

    def test_downloadable_inputs_have_audit_fields(self) -> None:
        required = {"retrieval_url", "retrieved_at", "license", "bytes", "sha256"}
        for source in self.sources:
            if "download_path" in source or "local_path" in source:
                self.assertFalse(required - source.keys(), source["id"])
                self.assertEqual(len(source["sha256"]), 64)
                self.assertGreater(source["bytes"], 0)

    def test_available_source_snapshots_match_manifest(self) -> None:
        checked = 0
        for source in self.sources:
            if "local_path" in source:
                path = ROOT / source["local_path"]
            elif "download_path" in source:
                path = ROOT / source["download_path"]
            else:
                continue
            if not path.exists():
                continue
            checked += 1
            self.assertEqual(path.stat().st_size, source["bytes"], source["id"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                source["sha256"],
                source["id"],
            )
        self.assertGreaterEqual(checked, 15)

    def test_operational_input_receipt_matches_local_files(self) -> None:
        receipts = (
            ROOT / "sources/epa-aqs/daily-pm25-2006-2026/receipt.json",
            ROOT / "sources/noaa-hms/annual-smoke-polygons-2006-2026/receipt.json",
        )
        records = []
        for receipt_path in receipts:
            records.extend(json.loads(receipt_path.read_text())["files"])
        self.assertEqual(len(records), 63)
        for record in records:
            path = ROOT / record["local_path"]
            self.assertTrue(path.exists(), record["local_path"])
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])

    def test_current_2026_receipt_matches_all_frozen_inputs(self) -> None:
        receipt = json.loads((ROOT / "sources/current-2026-receipt.json").read_text())
        self.assertEqual(receipt["publication_cutoff"], "2026-07-18")
        self.assertEqual(receipt["airnow_complete_day_cutoff"], "2026-07-18")
        records = receipt["files"] + receipt["airnow_daily_files"]
        self.assertEqual(len(receipt["airnow_daily_files"]), 48)
        self.assertEqual(len(records), 51)
        for record in records:
            path = ROOT / record["local_path"]
            self.assertTrue(path.exists(), record["local_path"])
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"]
            )

    def test_partial_latest_airnow_day_is_not_published(self) -> None:
        audit = json.loads(
            (ROOT / "sources/current-2026-availability-audit.json").read_text()
        )
        self.assertEqual(audit["decision"], "reject_partial_airnow_day")
        self.assertEqual(audit["latest_complete_common_cutoff"], "2026-07-18")
        candidate = audit["airnow"]["candidate_retained_us_pm25_sites"]
        complete = audit["airnow"]["prior_complete_retained_us_pm25_sites"]
        self.assertLess(candidate / complete, 0.5)

    def test_context_artifacts_are_frozen(self) -> None:
        self.assertEqual(len(self.manifest["context_artifacts"]), 3)
        for record in self.manifest["context_artifacts"]:
            path = ROOT / record["local_path"]
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                record["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
