#!/usr/bin/env python3
"""Freeze the official NIFC InFORM wildfire occurrence extension.

The live ArcGIS view changes continuously. This downloader first freezes the
matching ObjectID set, then retrieves those records in deterministic batches.
The compressed record snapshot remains an ignored provider-owned input; its
query, schema, byte count, checksum and per-year counts are tracked in a
committed receipt.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

from pipeline.settings import (
    NIFC_INFORM,
    NIFC_INFORM_RECORDS,
    NIFC_INFORM_SNAPSHOT_DATE,
    ROOT,
)


SERVICE_URL = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "InFORM_FireOccurrence_Public/FeatureServer/0"
)
QUERY_URL = f"{SERVICE_URL}/query"
WHERE = "CalendarYear BETWEEN 2021 AND 2026 AND IncidentTypeCategory = 'WF'"
OUT_FIELDS = (
    "OBJECTID", "GlobalID", "FORID", "UniqueFireIdentifier",
    "LocalIncidentIdentifier", "FireDiscoveryDateTime", "CalendarYear",
    "IncidentName", "IncidentSize", "CalculatedAcres", "FinalAcres",
    "InitialLatitude", "InitialLongitude", "POOState", "POOCounty", "POOFips",
    "FireCauseID", "ADSPermissionState", "FinalFireReportApprovedDate",
    "Status", "CreatedBySystem", "CreatedOnDateTime", "ModifiedOnDateTime",
)
USER_AGENT = "smoke-exposure/1.0 (+https://github.com/DanielSinclair/smoke-exposure)"
BATCH_SIZE = 2_000
WORKERS = 8


def request_json(url: str, parameters: dict[str, str], attempts: int = 5) -> dict:
    body = urllib.parse.urlencode(parameters).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return payload
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_batch(object_ids: list[int]) -> tuple[list[int], list[dict]]:
    payload = request_json(QUERY_URL, {
        "objectIds": ",".join(str(value) for value in object_ids),
        "outFields": ",".join(OUT_FIELDS),
        "returnGeometry": "false",
        "orderByFields": "OBJECTID",
        "f": "json",
    })
    features = payload.get("features", [])
    attributes = [feature["attributes"] for feature in features]
    returned_ids = {int(record["OBJECTID"]) for record in attributes}
    if not returned_ids.issubset(set(object_ids)):
        raise ValueError("InFORM batch returned an ObjectID outside the frozen request")
    return object_ids, attributes


def existing_receipt_is_valid() -> bool:
    receipt_path = NIFC_INFORM / "receipt.json"
    if not NIFC_INFORM_RECORDS.exists() or not receipt_path.exists():
        return False
    receipt = json.loads(receipt_path.read_text())
    return (
        receipt.get("sha256") == sha256(NIFC_INFORM_RECORDS)
        and receipt.get("bytes") == NIFC_INFORM_RECORDS.stat().st_size
        and receipt.get("query", {}).get("where") == WHERE
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.force and existing_receipt_is_valid():
        print(f"unchanged {NIFC_INFORM_RECORDS}")
        return

    NIFC_INFORM.mkdir(parents=True, exist_ok=True)
    layer = request_json(SERVICE_URL, {"f": "json"})
    id_payload = request_json(QUERY_URL, {
        "where": WHERE,
        "returnIdsOnly": "true",
        "f": "json",
    })
    object_ids = sorted(int(value) for value in id_payload.get("objectIds", []))
    if not object_ids or len(object_ids) != len(set(object_ids)):
        raise ValueError("InFORM ObjectID snapshot is empty or contains duplicates")

    partial = NIFC_INFORM_RECORDS.with_suffix(NIFC_INFORM_RECORDS.suffix + ".part")
    counts: Counter[int] = Counter()
    missing_object_ids: list[int] = []
    batches = [
        object_ids[index:index + BATCH_SIZE]
        for index in range(0, len(object_ids), BATCH_SIZE)
    ]
    with partial.open("wb") as binary:
        with gzip.GzipFile(filename="", mode="wb", fileobj=binary, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as output:
                for start in range(0, len(batches), WORKERS):
                    batch_group = batches[start:start + WORKERS]
                    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                        for requested_ids, records in executor.map(fetch_batch, batch_group):
                            returned_ids = {int(record["OBJECTID"]) for record in records}
                            missing_object_ids.extend(
                                object_id for object_id in requested_ids if object_id not in returned_ids
                            )
                            for record in records:
                                counts[int(record["CalendarYear"])] += 1
                                output.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False))
                                output.write("\n")
    partial.replace(NIFC_INFORM_RECORDS)

    if sum(counts.values()) + len(missing_object_ids) != len(object_ids):
        raise ValueError("InFORM written and missing records do not reconcile to frozen ObjectIDs")
    receipt = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": NIFC_INFORM_SNAPSHOT_DATE,
        "source_url": SERVICE_URL,
        "service_item_id": layer.get("serviceItemId"),
        "layer_name": layer.get("name"),
        "layer_last_edit_epoch_ms": layer.get("editingInfo", {}).get("lastEditDate"),
        "query": {
            "where": WHERE,
            "out_fields": list(OUT_FIELDS),
            "return_geometry": False,
        },
        "object_id_count": len(object_ids),
        "record_count": sum(counts.values()),
        "missing_object_id_count": len(missing_object_ids),
        "missing_object_ids": missing_object_ids,
        "records_by_year": {str(year): counts[year] for year in sorted(counts)},
        "coverage_note": (
            "Public InFORM wildfire occurrence records, including approved and unapproved "
            "records. Certification status is retained; counts are source-covered and do not "
            "replace NIFC official annual statistics."
        ),
        "local_path": str(NIFC_INFORM_RECORDS.relative_to(ROOT)),
        "bytes": NIFC_INFORM_RECORDS.stat().st_size,
        "sha256": sha256(NIFC_INFORM_RECORDS),
    }
    receipt_path = NIFC_INFORM / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        f"wrote {NIFC_INFORM_RECORDS} with {sum(counts.values()):,} records "
        f"({len(missing_object_ids):,} frozen IDs changed before retrieval)"
    )
    print(f"wrote {receipt_path}")


if __name__ == "__main__":
    main()
