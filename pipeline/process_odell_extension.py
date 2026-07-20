#!/usr/bin/env python3
"""Aggregate every locally available O'Dell/Ford Dryad mean-background grid.

The Dryad release packages 2006-2023 in one 5.71 GB archive and 2024 in a
standalone 317 MB archive. This processor extracts one netCDF member at a time,
maps its grid to fixed 2020 ZCTA centroids, and removes the temporary netCDF
before moving to the next year. It never requires both large Dryad products or
all uncompressed years to coexist on disk.
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

import netCDF4
import numpy as np

from pipeline.process_smoke import load_zctas, nearest_grid_indices
from pipeline.settings import (
    AQI_101_PM25_UG_M3,
    BROAD_EXPOSURE_POPULATION,
    ODELL_DRYAD_DOWNLOADS,
    PROCESSED,
)


MODEL_ID = "ODELL_FORD_DRYAD_MEAN_BACKGROUND_V5"
ARCHIVES = {
    "2006_2023_Mean_Background.zip": {
        "sha256": "194bbd9c1e2df245df3e6c0d9ffd3aa83d281feb7d7708214613099f624c5c26",
        "expected_years": list(range(2006, 2024)),
        "bytes": 5_707_923_964,
    },
    "2024_Mean_Background.zip": {
        "sha256": "fde514284b1014a803611e80fd004182608e47e8dbabc9675355a9e8a6b514b8",
        "expected_years": [2024],
        "bytes": 317_436_480,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def member_year(member: str) -> int | None:
    matches = re.findall(r"(?:19|20)\d{2}", Path(member).name)
    if not matches:
        return None
    year = int(matches[-1])
    return year if 2006 <= year <= 2024 else None


def discover_members() -> tuple[dict[int, tuple[Path, str]], list[dict[str, object]]]:
    members: dict[int, tuple[Path, str]] = {}
    archive_audit: list[dict[str, object]] = []
    for filename, metadata in ARCHIVES.items():
        path = ODELL_DRYAD_DOWNLOADS / filename
        if not path.exists():
            archive_audit.append({
                "filename": filename,
                "available_locally": False,
                **metadata,
            })
            continue
        actual_sha = sha256(path)
        if actual_sha != metadata["sha256"]:
            raise ValueError(f"checksum mismatch for {path}")
        archive_years: list[int] = []
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".nc"):
                    continue
                year = member_year(name)
                if year is None:
                    continue
                if year in members:
                    raise ValueError(f"duplicate O'Dell netCDF for {year}")
                members[year] = (path, name)
                archive_years.append(year)
        expected = list(metadata["expected_years"])
        if sorted(archive_years) != expected:
            raise ValueError(
                f"{filename} years {sorted(archive_years)} do not match expected {expected}"
            )
        archive_audit.append({
            "filename": filename,
            "available_locally": True,
            "actual_sha256": actual_sha,
            "member_years": sorted(archive_years),
            **metadata,
        })
    return members, archive_audit


def deterministic_gzip_writer(path: Path):
    raw = path.open("wb")
    compressed = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
    text = io.TextIOWrapper(compressed, encoding="utf-8", newline="")
    return raw, compressed, text


def process_year(
    year: int,
    archive_path: Path,
    member: str,
    zctas: list[dict[str, object]],
    locality_writer: csv.DictWriter,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    with zipfile.ZipFile(archive_path) as archive:
        member_info = archive.getinfo(member)
        free_bytes = shutil.disk_usage(archive_path.parent).free
        required = member_info.file_size + 512 * 1024 * 1024
        if free_bytes < required:
            raise OSError(
                f"need at least {required:,} free bytes to extract {member}; have {free_bytes:,}"
            )
        with tempfile.TemporaryDirectory(prefix=f"odell-{year}-") as temp_dir:
            netcdf_path = Path(temp_dir) / f"odell_{year}.nc"
            with archive.open(member) as source, netcdf_path.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)

            populations = np.asarray([row["population"] for row in zctas], dtype=np.int64)
            smoke_days = np.zeros(len(zctas), dtype=np.int16)
            smoke_sum = np.zeros(len(zctas), dtype=np.float64)
            residents_ever = np.zeros(len(zctas), dtype=bool)
            daily_rows: list[dict[str, object]] = []
            with netCDF4.Dataset(netcdf_path) as dataset:
                required_variables = {"lon", "lat", "doy", "PM25", "Background_PM25", "HMS_Smoke"}
                missing = required_variables - set(dataset.variables)
                if missing:
                    raise ValueError(f"{member} is missing variables {sorted(missing)}")
                lons = np.asarray(dataset.variables["lon"][:])
                lats = np.asarray(dataset.variables["lat"][:])
                first_total = np.ma.filled(dataset.variables["PM25"][0], np.nan)
                first_background = np.ma.filled(dataset.variables["Background_PM25"][0], np.nan)
                valid = np.isfinite(first_total) & np.isfinite(first_background)
                grid_indices, distances_km = nearest_grid_indices(zctas, lats, lons, valid)
                day_of_year = np.asarray(dataset.variables["doy"][:], dtype=int)
                expected_days = 366 if dt.date(year, 12, 31).timetuple().tm_yday == 366 else 365
                if len(day_of_year) != expected_days or sorted(day_of_year.tolist()) != list(range(1, expected_days + 1)):
                    raise ValueError(f"{member} does not contain one row for every day in {year}")

                for day_index, doy in enumerate(day_of_year):
                    total = np.ma.filled(dataset.variables["PM25"][day_index], np.nan).ravel()[grid_indices]
                    background = np.ma.filled(dataset.variables["Background_PM25"][day_index], np.nan).ravel()[grid_indices]
                    hms = np.ma.filled(dataset.variables["HMS_Smoke"][day_index], 0).ravel()[grid_indices]
                    enhancement = total - background
                    smoke_attributed = np.where(hms >= 0.5, enhancement, 0.0)
                    smoke_sum += np.nan_to_num(smoke_attributed, nan=0.0)
                    high = (hms >= 0.5) & np.isfinite(enhancement) & (enhancement >= AQI_101_PM25_UG_M3)
                    smoke_days += high.astype(np.int16)
                    residents_ever |= high
                    exposed_population = int(populations[high].sum())
                    day_date = dt.date(year, 1, 1) + dt.timedelta(days=int(doy) - 1)
                    daily_rows.append({
                        "date": day_date.isoformat(),
                        "year": year,
                        "model_id": MODEL_ID,
                        "population_exposed": exposed_population,
                        "zctas_exposed": int(high.sum()),
                        "broad_smoke_day": int(exposed_population >= BROAD_EXPOSURE_POPULATION),
                        "comparable_to_stanford": "false",
                    })

            for index, row in enumerate(zctas):
                locality_writer.writerow({
                    "year": year,
                    "zcta": row["zcta"],
                    "name": row["name"],
                    "state": row["state"],
                    "population_2020": row["population"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "grid_distance_km": round(float(distances_km[index]), 3),
                    "smoke_days_aqi101_equiv": int(smoke_days[index]),
                    "mean_smoke_pm25_ug_m3": round(float(smoke_sum[index] / len(daily_rows)), 3),
                    "population_days": int(populations[index] * smoke_days[index]),
                    "model_id": MODEL_ID,
                    "comparable_to_stanford": "false",
                })

            peak = max(daily_rows, key=lambda row: int(row["population_exposed"]))
            annual = {
                "year": year,
                "model_id": MODEL_ID,
                "background_method": "seasonal_mean_no_hms_smoke_days",
                "broad_smoke_days": sum(int(row["broad_smoke_day"]) for row in daily_rows),
                "population_days": sum(int(row["population_exposed"]) for row in daily_rows),
                "peak_population_exposed": peak["population_exposed"],
                "peak_date": peak["date"],
                "residents_exposed_at_least_once": int(populations[residents_ever].sum()),
                "zctas": len(zctas),
                "population_reference": int(populations.sum()),
                "mean_grid_distance_km": round(float(np.mean(distances_km)), 3),
                "p95_grid_distance_km": round(float(np.percentile(distances_km, 95)), 3),
                "source_archive": archive_path.name,
                "source_member": member,
                "comparable_to_stanford": "false",
            }
            return daily_rows, annual


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    members, archive_audit = discover_members()
    if not members:
        raise FileNotFoundError(
            f"no O'Dell/Ford mean-background archives found under {ODELL_DRYAD_DOWNLOADS}"
        )
    zctas = load_zctas()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    locality_path = PROCESSED / "odell_zcta_exposure_released_years.csv.gz"
    locality_part = locality_path.with_suffix(locality_path.suffix + ".part")
    locality_part.unlink(missing_ok=True)
    raw, compressed, text = deterministic_gzip_writer(locality_part)
    daily_rows: list[dict[str, object]] = []
    annual_rows: list[dict[str, object]] = []
    try:
        fieldnames = [
            "year", "zcta", "name", "state", "population_2020", "latitude", "longitude",
            "grid_distance_km", "smoke_days_aqi101_equiv", "mean_smoke_pm25_ug_m3",
            "population_days", "model_id", "comparable_to_stanford",
        ]
        writer = csv.DictWriter(text, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for year, (archive_path, member) in sorted(members.items()):
            year_daily, annual = process_year(year, archive_path, member, zctas, writer)
            daily_rows.extend(year_daily)
            annual_rows.append(annual)
            print(f"processed O'Dell/Ford {year}: {len(year_daily)} days, {len(zctas):,} ZCTAs")
    except Exception:
        text.close()
        compressed.close()
        raw.close()
        locality_part.unlink(missing_ok=True)
        raise
    else:
        text.close()
        compressed.close()
        raw.close()
        locality_part.replace(locality_path)

    write_csv(PROCESSED / "odell_smoke_daily_released_years.csv", daily_rows)
    write_csv(PROCESSED / "odell_smoke_annual_released_years.csv", annual_rows)
    processed_years = [int(row["year"]) for row in annual_rows]
    missing_years = sorted(set(range(2006, 2025)) - set(processed_years))
    audit = {
        "model_id": MODEL_ID,
        "processed_years": processed_years,
        "missing_released_years": missing_years,
        "archives": archive_audit,
        "source_release_bytes": {
            "2006_2023_mean_archive": ARCHIVES["2006_2023_Mean_Background.zip"]["bytes"],
            "2024_mean_archive": ARCHIVES["2024_Mean_Background.zip"]["bytes"],
        },
        "storage_strategy": "one netCDF member extracted to an auto-deleted temporary directory at a time",
        "comparability": {
            "stanford": False,
            "reason": (
                "O'Dell/Ford uses a separate kriged monitor-plus-HMS method on a 15 km grid; "
                "these outputs are an independent released-model series, not Stanford continuation."
            ),
        },
        "release_blocker": (
            None if not missing_years else
            "The public 2006-2023 mean-background archive is 5,707,923,964 bytes. "
            "It was intentionally not downloaded on a nearly full workstation. Run the pinned "
            "download on a volume with at least 8 GB free, then rerun this processor; it will "
            "extract and delete one annual netCDF at a time."
        ),
    }
    (PROCESSED / "odell_processing_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(f"wrote O'Dell/Ford outputs for years {processed_years}")


if __name__ == "__main__":
    main()
