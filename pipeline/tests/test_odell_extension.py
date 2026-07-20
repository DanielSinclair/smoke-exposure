"""Unit tests for the storage-bounded O'Dell/Ford released-grid processor."""

from __future__ import annotations

import csv
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

import netCDF4
import numpy as np

from pipeline.process_odell_extension import MODEL_ID, member_year, process_year


class OdellExtensionTests(unittest.TestCase):
    def test_member_year_parser(self) -> None:
        self.assertEqual(member_year("mean/krigedPM25_2024_4repo.nc"), 2024)
        self.assertEqual(member_year("2006_2023/krigedPM25_2011.nc"), 2011)
        self.assertIsNone(member_year("README.nc"))

    def test_one_year_grid_is_aggregated_without_persistent_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            netcdf_path = directory / "krigedPM25_2023.nc"
            with netCDF4.Dataset(netcdf_path, "w") as dataset:
                dataset.createDimension("date", 365)
                dataset.createDimension("x", 2)
                dataset.createDimension("y", 2)
                dataset.createVariable("doy", "i4", ("date",))[:] = np.arange(1, 366)
                lons = dataset.createVariable("lon", "f8", ("x", "y"))
                lats = dataset.createVariable("lat", "f8", ("x", "y"))
                lons[:] = [[-100.0, -99.0], [-100.0, -99.0]]
                lats[:] = [[40.0, 40.0], [41.0, 41.0]]
                total = dataset.createVariable("PM25", "f8", ("date", "x", "y"))
                background = dataset.createVariable("Background_PM25", "f8", ("date", "x", "y"))
                smoke = dataset.createVariable("HMS_Smoke", "f8", ("date", "x", "y"))
                total[:] = 0
                background[:] = 0
                smoke[:] = 0
                total[0, 0, 0] = 40
                smoke[0, 0, 0] = 1
            archive_path = directory / "synthetic.zip"
            member = "release/krigedPM25_2023.nc"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(netcdf_path, member)
            netcdf_path.unlink()

            zctas = [{
                "zcta": "00001", "name": "Test", "state": "CO",
                "population": 11_000_000, "latitude": 40.0, "longitude": -100.0,
            }]
            locality_buffer = io.StringIO()
            fieldnames = [
                "year", "zcta", "name", "state", "population_2020", "latitude", "longitude",
                "grid_distance_km", "smoke_days_aqi101_equiv", "mean_smoke_pm25_ug_m3",
                "population_days", "model_id", "comparable_to_stanford",
            ]
            writer = csv.DictWriter(locality_buffer, fieldnames=fieldnames)
            writer.writeheader()
            daily, annual = process_year(2023, archive_path, member, zctas, writer)

        self.assertEqual(len(daily), 365)
        self.assertEqual(daily[0]["population_exposed"], 11_000_000)
        self.assertEqual(annual["broad_smoke_days"], 1)
        self.assertEqual(annual["population_days"], 11_000_000)
        self.assertEqual(annual["model_id"], MODEL_ID)
        self.assertEqual(annual["comparable_to_stanford"], "false")
        self.assertIn("00001", locality_buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
