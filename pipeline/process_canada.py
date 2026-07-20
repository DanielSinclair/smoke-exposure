#!/usr/bin/env python3
"""Extract Canada's annual NBAC burned-area series from the official workbook.

The input is a versioned Natural Resources Canada workbook.  This parser uses
only the Python standard library so the provenance path remains runnable without
Excel, pandas, or an office-suite conversion step.
"""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "sources/nrcan-nbac/NBAC_summarystats_1972_to_2025_20260513.xlsx"
DEFAULT_OUTPUT = ROOT / "data/processed/canada_fire_annual.csv"

SOURCE_URL = (
    "https://cwfis.cfs.nrcan.gc.ca/downloads/nbac/"
    "NBAC_summarystats_1972_to_2025_20260513.xlsx"
)
SOURCE_DATASET = "NRCan CFS National Burned Area Composite (NBAC)"
SOURCE_VERSION = "20260513"
SOURCE_AS_OF_DATE = "2026-05-13"
ACRES_PER_HECTARE = Decimal("2.471053814671653")

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS, "pr": PKG_REL_NS}


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall("m:si", NS)
    ]


def _sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = None
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]
            break
    if relationship_id is None:
        raise ValueError(f"Workbook has no sheet named {sheet_name!r}")

    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in relationships.findall("pr:Relationship", NS):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib["Target"].lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError(f"Workbook relationship {relationship_id!r} is missing")


def _column_name(cell_reference: str) -> str:
    match = re.match(r"([A-Z]+)", cell_reference)
    if not match:
        raise ValueError(f"Invalid XLSX cell reference: {cell_reference!r}")
    return match.group(1)


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("m:v", NS)
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t")
        )
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        return shared_strings[int(value.text)]
    return value.text


def read_nbac_national_rows(input_path: Path) -> list[tuple[int, Decimal]]:
    """Return one ``(year, adjusted_hectares)`` row per NBAC year."""

    with zipfile.ZipFile(input_path) as archive:
        strings = _shared_strings(archive)
        sheet = ET.fromstring(
            archive.read(_sheet_path(archive, "sumstats_admin_name"))
        )

    records: list[dict[str, str]] = []
    for row in sheet.findall(".//m:sheetData/m:row", NS):
        records.append(
            {
                _column_name(cell.attrib["r"]): _cell_value(cell, strings)
                for cell in row.findall("m:c", NS)
            }
        )

    header = next(
        (record for record in records if record.get("A") == "YEAR"), None
    )
    if header is None:
        raise ValueError("Could not locate the YEAR header in the NBAC summary sheet")
    canada_column = next(
        (column for column, label in header.items() if label == "CANADA"), None
    )
    if canada_column is None:
        raise ValueError("Could not locate the CANADA total column")

    annual: list[tuple[int, Decimal]] = []
    for record in records:
        if not record.get("A", "").isdigit() or not record.get(canada_column):
            continue
        year = int(record["A"])
        if 1972 <= year <= 2025:
            annual.append((year, Decimal(record[canada_column])))

    annual.sort(key=lambda item: item[0])
    years = [year for year, _ in annual]
    expected = list(range(1972, 2026))
    if years != expected:
        missing = sorted(set(expected) - set(years))
        duplicates = sorted({year for year in years if years.count(year) > 1})
        raise ValueError(
            f"NBAC annual coverage is not 1972-2025: "
            f"missing={missing}, duplicates={duplicates}"
        )
    return annual


def write_output(rows: list[tuple[int, Decimal]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "year",
        "geography",
        "burned_area_ha",
        "burned_area_acres",
        "fire_count",
        "source_dataset",
        "source_version",
        "source_url",
        "as_of_date",
        "status",
        "complete",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for year, hectares in rows:
            acres = (hectares * ACRES_PER_HECTARE).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
            writer.writerow(
                {
                    "year": year,
                    "geography": "Canada",
                    "burned_area_ha": format(hectares, "f"),
                    "burned_area_acres": format(acres, "f"),
                    # Intentionally blank: the NBAC area product does not provide
                    # a comparable annual ignition/fire count. See source README.
                    "fire_count": "",
                    "source_dataset": SOURCE_DATASET,
                    "source_version": SOURCE_VERSION,
                    "source_url": SOURCE_URL,
                    "as_of_date": SOURCE_AS_OF_DATE,
                    "status": "annual_complete_revisionable",
                    "complete": "true",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_nbac_national_rows(args.input)
    write_output(rows, args.output)
    print(
        f"Wrote {len(rows)} complete annual NBAC observations "
        f"({rows[0][0]}-{rows[-1][0]}) to {args.output}"
    )


if __name__ == "__main__":
    main()
