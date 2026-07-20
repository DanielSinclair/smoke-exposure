#!/usr/bin/env python3
"""Map released O'Dell/Ford 2021 smoke PM2.5 grid values to ZCTA centroids.

The source grid is finer than ZCTAs (15 km). Each CONUS ZCTA is represented by
its 2020 Census internal point and assigned the nearest valid grid-cell center.
This is a transparent demo mapping, not an area-weighted polygon overlay.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import netCDF4
import numpy as np

from pipeline.settings import (
    AQI_101_PM25_UG_M3,
    BROAD_EXPOSURE_POPULATION,
    ODELL_2021_DOWNLOADS,
    ODELL_2021_WORKING,
    PROCESSED,
)


ARCHIVE = ODELL_2021_DOWNLOADS / "Ford_PM25_2021.zip"
ARCHIVE_SHA256 = "7324ff4468af4814b297feff5cff3dde1e18e4ed2f1663cda6c2cccd3fc74f4b"
MEMBER = "Ford_PM25_2021/krigedPM25_2021_4repo.nc"
NETCDF = ODELL_2021_WORKING / "ford2021" / MEMBER
EXCLUDED_STATES = {"AK", "HI", "PR"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_netcdf() -> None:
    if sha256(ARCHIVE) != ARCHIVE_SHA256:
        raise ValueError("Ford_PM25_2021.zip checksum mismatch")
    if NETCDF.exists():
        return
    NETCDF.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as archive:
        archive.extract(MEMBER, ODELL_2021_WORKING / "ford2021")


def load_zctas() -> list[dict[str, object]]:
    with (PROCESSED / "zcta_2020.csv").open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            state = row["state"]
            # The released smoke grid covers the contiguous United States.
            # DC is included. Alaska, Hawaii, Puerto Rico, territories, and
            # records without a Census dominant-state assignment are excluded.
            if not state or state in EXCLUDED_STATES:
                continue
            rows.append({
                "zcta": row["zcta"],
                "name": row["name"],
                "state": state,
                "population": int(row["population_2020"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            })
        return rows


def nearest_grid_indices(
    zctas: list[dict[str, object]], lats: np.ndarray, lons: np.ndarray, valid: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    flat_valid = np.flatnonzero(valid.ravel())
    grid_lat = lats.ravel()[flat_valid]
    grid_lon = lons.ravel()[flat_valid]
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for position, (lat, lon) in enumerate(zip(grid_lat, grid_lon)):
        buckets[(math.floor(float(lat)), math.floor(float(lon)))].append(position)

    targets: list[int] = []
    distances_km: list[float] = []
    for zcta in zctas:
        lat = float(zcta["latitude"])
        lon = float(zcta["longitude"])
        candidates: list[int] = []
        for radius in (1, 2, 4):
            for lat_bin in range(math.floor(lat) - radius, math.floor(lat) + radius + 1):
                for lon_bin in range(math.floor(lon) - radius, math.floor(lon) + radius + 1):
                    candidates.extend(buckets.get((lat_bin, lon_bin), ()))
            if candidates:
                break
        if not candidates:
            raise ValueError(f"no grid candidate for ZCTA {zcta['zcta']}")
        candidate_array = np.asarray(candidates, dtype=np.int64)
        lat_delta = grid_lat[candidate_array] - lat
        lon_delta = (grid_lon[candidate_array] - lon) * math.cos(math.radians(lat))
        distance_sq = lat_delta * lat_delta + lon_delta * lon_delta
        nearest_position = candidate_array[int(np.argmin(distance_sq))]
        targets.append(int(flat_valid[nearest_position]))
        distances_km.append(float(math.sqrt(float(np.min(distance_sq))) * 111.195))
    return np.asarray(targets, dtype=np.int64), np.asarray(distances_km)


def main() -> None:
    ensure_netcdf()
    zctas = load_zctas()
    populations = np.asarray([row["population"] for row in zctas], dtype=np.int64)
    smoke_days = np.zeros(len(zctas), dtype=np.int16)
    smoke_sum = np.zeros(len(zctas), dtype=np.float64)
    daily_rows: list[dict[str, object]] = []

    with netCDF4.Dataset(NETCDF) as dataset:
        lons = np.asarray(dataset.variables["lon"][:])
        lats = np.asarray(dataset.variables["lat"][:])
        first_total = np.ma.filled(dataset.variables["PM25"][0], np.nan)
        first_background = np.ma.filled(dataset.variables["Background_PM25"][0], np.nan)
        valid = np.isfinite(first_total) & np.isfinite(first_background)
        grid_indices, distances_km = nearest_grid_indices(zctas, lats, lons, valid)
        day_of_year = np.asarray(dataset.variables["doy"][:], dtype=int)

        for day_index, doy in enumerate(day_of_year):
            total = np.ma.filled(dataset.variables["PM25"][day_index], np.nan).ravel()[grid_indices]
            background = np.ma.filled(dataset.variables["Background_PM25"][day_index], np.nan).ravel()[grid_indices]
            hms = np.ma.filled(dataset.variables["HMS_Smoke"][day_index], 0).ravel()[grid_indices]
            enhancement = total - background
            smoke_attributed = np.where(hms >= 0.5, enhancement, 0.0)
            smoke_sum += np.nan_to_num(smoke_attributed, nan=0.0)
            high = (hms >= 0.5) & np.isfinite(enhancement) & (enhancement >= AQI_101_PM25_UG_M3)
            smoke_days += high.astype(np.int16)
            exposed_population = int(populations[high].sum())
            date = dt.date(2021, 1, 1) + dt.timedelta(days=int(doy) - 1)
            daily_rows.append({
                "date": date.isoformat(),
                "population_exposed": exposed_population,
                "zctas_exposed": int(high.sum()),
                "broad_smoke_day": int(exposed_population >= BROAD_EXPOSURE_POPULATION),
            })

    PROCESSED.mkdir(parents=True, exist_ok=True)
    locality_out = PROCESSED / "zcta_smoke_exposure_2021.csv"
    with locality_out.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "zcta", "name", "state", "population_2020", "latitude", "longitude",
            "grid_distance_km", "smoke_days_aqi101_equiv", "mean_smoke_pm25_ug_m3", "population_days",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for index, row in enumerate(zctas):
            writer.writerow({
                "zcta": row["zcta"], "name": row["name"], "state": row["state"],
                "population_2020": row["population"], "latitude": row["latitude"],
                "longitude": row["longitude"], "grid_distance_km": round(float(distances_km[index]), 3),
                "smoke_days_aqi101_equiv": int(smoke_days[index]),
                "mean_smoke_pm25_ug_m3": round(float(smoke_sum[index] / 365.0), 3),
                "population_days": int(populations[index] * smoke_days[index]),
            })

    daily_out = PROCESSED / "zcta_smoke_daily_national_2021.csv"
    with daily_out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(daily_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(daily_rows)

    annual_out = PROCESSED / "smoke_annual_2021.csv"
    peak = max(daily_rows, key=lambda row: int(row["population_exposed"]))
    with annual_out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "year", "broad_smoke_days", "population_days",
                "peak_population_exposed", "peak_date",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow({
            "year": 2021,
            "broad_smoke_days": sum(int(row["broad_smoke_day"]) for row in daily_rows),
            "population_days": sum(int(row["population_exposed"]) for row in daily_rows),
            "peak_population_exposed": peak["population_exposed"],
            "peak_date": peak["date"],
        })
    print(f"wrote actual grid-derived exposure for {len(zctas):,} CONUS ZCTAs")


if __name__ == "__main__":
    main()
