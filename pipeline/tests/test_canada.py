#!/usr/bin/env python3
"""Executable integrity tests for the Canadian NBAC annual extract."""

from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "sources/nrcan-nbac/NBAC_summarystats_1972_to_2025_20260513.xlsx"
OUTPUT = ROOT / "data/processed/canada_fire_annual.csv"
PROCESSOR = ROOT / "pipeline/process_canada.py"
EXPECTED_SHA256 = "9248134616e43740a596fce592e7ac72e0bd41334de831f4712a3f37cc2bcefc"
ACRES_PER_HECTARE = Decimal("2.471053814671653")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class CanadaNbacTests(unittest.TestCase):
    def test_versioned_raw_snapshot_checksum(self) -> None:
        digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_SHA256)

    def test_published_extract_matches_fresh_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rebuilt = Path(temp_dir) / "canada_fire_annual.csv"
            subprocess.run(
                [
                    sys.executable,
                    str(PROCESSOR),
                    "--input",
                    str(SOURCE),
                    "--output",
                    str(rebuilt),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(rebuilt.read_bytes(), OUTPUT.read_bytes())

    def test_coverage_grain_and_completeness(self) -> None:
        rows = read_rows(OUTPUT)
        years = [int(row["year"]) for row in rows]
        self.assertEqual(years, list(range(1972, 2026)))
        self.assertNotIn(2026, years)
        self.assertTrue(all(row["geography"] == "Canada" for row in rows))
        self.assertTrue(all(row["complete"] == "true" for row in rows))
        self.assertTrue(
            all(row["status"] == "annual_complete_revisionable" for row in rows)
        )

    def test_values_and_units(self) -> None:
        rows = {int(row["year"]): row for row in read_rows(OUTPUT)}
        self.assertEqual(
            Decimal(rows[2023]["burned_area_ha"]),
            Decimal("14796428.054547966"),
        )
        self.assertEqual(
            Decimal(rows[2025]["burned_area_ha"]),
            Decimal("7307708.670613613"),
        )
        for row in rows.values():
            hectares = Decimal(row["burned_area_ha"])
            acres = Decimal(row["burned_area_acres"])
            self.assertGreater(hectares, 0)
            self.assertLess(abs(acres / hectares - ACRES_PER_HECTARE), Decimal("1e-6"))

    def test_fire_counts_are_explicitly_not_spliced(self) -> None:
        rows = read_rows(OUTPUT)
        self.assertTrue(all(row["fire_count"] == "" for row in rows))


if __name__ == "__main__":
    unittest.main()
