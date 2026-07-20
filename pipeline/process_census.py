#!/usr/bin/env python3
"""Build a 2020 Census ZCTA population/centroid dimension."""

from __future__ import annotations

import csv
import io
import json
import zipfile

from pipeline.settings import CENSUS_2020, PROCESSED


STATE_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "72": "PR",
}


def load_population() -> dict[str, tuple[int, str]]:
    payload = json.loads((CENSUS_2020 / "DECENNIALDHC2020_P1_ZCTA.json").read_text())
    rows = payload["response"]["data"]
    header = rows[0]
    idx = {name: position for position, name in enumerate(header)}
    return {
        row[idx["GEO_ID"]][-5:]: (int(row[idx["P1_001N"]]), row[idx["NAME"]])
        for row in rows[1:]
    }


def load_centroids() -> dict[str, dict[str, float]]:
    archive = CENSUS_2020 / "2020_Gaz_zcta_national.zip"
    with zipfile.ZipFile(archive) as zf:
        name = zf.namelist()[0]
        text = io.TextIOWrapper(zf.open(name), encoding="utf-8-sig")
        rows = csv.reader(text, delimiter="\t")
        header = [value.strip() for value in next(rows)]
        parsed = {}
        for raw in rows:
            row = dict(zip(header, (value.strip() for value in raw)))
            parsed[row["GEOID"]] = {
                "latitude": float(row["INTPTLAT"]),
                "longitude": float(row["INTPTLONG"]),
                "land_sq_mi": float(row["ALAND_SQMI"]),
            }
        return parsed


def load_dominant_state() -> dict[str, str]:
    """Assign each ZCTA to the state containing its largest land-area share."""
    path = CENSUS_2020 / "tab20_zcta520_county20_natl.txt"
    best: dict[str, tuple[int, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="|"):
            zcta = row["GEOID_ZCTA5_20"]
            county = row["GEOID_COUNTY_20"]
            if not zcta or not county:
                continue
            area = int(row["AREALAND_PART"] or 0)
            if zcta not in best or area > best[zcta][0]:
                best[zcta] = (area, STATE_ABBR.get(county[:2], county[:2]))
    return {zcta: value[1] for zcta, value in best.items()}


def main() -> None:
    population = load_population()
    centroids = load_centroids()
    states = load_dominant_state()
    keys = sorted(population.keys() & centroids.keys())
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "zcta_2020.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "zcta", "name", "state", "population_2020", "latitude",
                "longitude", "land_sq_mi",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for zcta in keys:
            pop, name = population[zcta]
            writer.writerow({
                "zcta": zcta,
                "name": name,
                "state": states.get(zcta, ""),
                "population_2020": pop,
                **centroids[zcta],
            })
    print(f"wrote {len(keys):,} ZCTAs to {out}")


if __name__ == "__main__":
    main()
