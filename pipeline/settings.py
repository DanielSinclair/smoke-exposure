from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
MANIFEST = SOURCES / "manifest.json"
CENSUS_2020 = SOURCES / "census" / "2020"
STANFORD_V2 = SOURCES / "stanford-echo" / "v2-beta" / "downloads"
ODELL_2021 = SOURCES / "odell-ford" / "2021"
ODELL_2021_DOWNLOADS = ODELL_2021 / "downloads"
ODELL_2021_WORKING = ODELL_2021 / "working"
ODELL_DRYAD_V5 = SOURCES / "odell-ford" / "dryad-v5"
ODELL_DRYAD_DOWNLOADS = ODELL_DRYAD_V5 / "downloads"
ODELL_DRYAD_WORKING = ODELL_DRYAD_V5 / "working"
EPA_AQS_2006_2026 = SOURCES / "epa-aqs" / "daily-pm25-2006-2026"
EPA_AQS_DOWNLOADS = EPA_AQS_2006_2026 / "downloads"
EPA_AIRNOW = SOURCES / "epa-airnow"
EPA_AIRNOW_2026 = EPA_AIRNOW / "2026"
EPA_AIRNOW_DAILY = EPA_AIRNOW_2026 / "daily"
NOAA_HMS_2006_2026 = SOURCES / "noaa-hms" / "annual-smoke-polygons-2006-2026"
NOAA_HMS_DOWNLOADS = NOAA_HMS_2006_2026 / "downloads"
MTBS_SOURCE = SOURCES / "mtbs" / "S_USA.MTBS_FIRE_OCCURRENCE_PT.zip"
NRCAN_NBAC_SOURCE = SOURCES / "nrcan-nbac" / "NBAC_summarystats_1972_to_2025_20260513.xlsx"
NRCAN_NFDB_LARGE_FIRES_SOURCE = (
    SOURCES / "nrcan-nfdb" / "2026-06-08" / "NFDB_point_large_fires_txt.zip"
)
NIFC_INFORM_SNAPSHOT_DATE = "2026-07-20"
NIFC_INFORM = SOURCES / "nifc-inform" / NIFC_INFORM_SNAPSHOT_DATE
NIFC_INFORM_RECORDS = NIFC_INFORM / "wildfire_records_2021_2026.ndjson.gz"
HISTORICAL_SMOKE_EVIDENCE = SOURCES / "historical-smoke-evidence" / "v1"
NOAA_STORM_EVENTS_1950_2005 = SOURCES / "noaa-storm-events" / "1950-2005"
NOAA_STORM_EVENTS_DOWNLOADS = NOAA_STORM_EVENTS_1950_2005 / "downloads"
PROCESSED = ROOT / "data" / "processed"
PROCESSED_CHECKSUMS = ROOT / "data" / "processed_checksums.json"

CURRENT_DATA_DATE = "2026-07-18"
AIRNOW_SUPPLEMENT_START_DATE = "2026-06-01"
AIRNOW_SUPPLEMENT_END_DATE = "2026-07-18"

AQI_101_PM25_UG_M3 = 35.5
BROAD_EXPOSURE_POPULATION = 10_000_000

# The legacy validation keeps the released O'Dell/Ford 2021 seasonal-median-
# background product. The separate Dryad v5 processor uses publisher-recommended
# mean-background grids for every checksum-verified released year available locally.
SMOKE_YEAR = 2021
