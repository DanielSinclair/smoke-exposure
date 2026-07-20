# Data pipeline

The Python pipeline rebuilds the datasets behind the U.S. Wildfire Smoke Exposure Trend report. It keeps the comparable Stanford smoke series, independent O'Dell/Ford released-model checks, the 2006–2026 monitor-plus-satellite screen, and fire-activity records as separate products.

## Run

Python 3.11+ is recommended.

```bash
python3 -m venv .venv
.venv/bin/pip install -r pipeline/requirements.txt
.venv/bin/python -m pipeline.run_all --download
.venv/bin/python -m unittest discover -s pipeline/tests -v
```

Use `--download` for the first build or an intentional source refresh. A local rebuild can omit it after the ignored provider downloads are present.

## Pipeline stages

| Module | Responsibility |
| --- | --- |
| `download.py` | Fetch manifest-pinned Census, Stanford, O'Dell/Ford, and provider inputs |
| `download_extension_inputs.py` | Fetch EPA AQS and NOAA HMS annual files for the complete 2006–2026 monitor screen |
| `download_current_inputs.py` | Freeze the current AirNow, NIFC, and NRCan operational inputs |
| `download_fire_history_inputs.py` | Freeze comprehensive U.S. and Canadian fire-record archives |
| `download_historical_smoke_inputs.py` | Freeze NOAA Storm Events annual detail files for the pre-2006 candidate screen |
| `process_census.py` | Build the fixed 2020 county/ZCTA population geography |
| `aggregate_stanford.py` | Aggregate Stanford county-day smoke estimates into national daily and annual exposure metrics |
| `process_smoke.py` | Map the released 2021 O'Dell/Ford grid to Census ZCTAs for independent validation |
| `process_odell_extension.py` | Stream locally available Dryad mean-background archives one year at a time into ZCTA, daily, and annual released-model outputs |
| `process_operational_extension.py` | Match 2006–2026 high-PM2.5 monitor-days to NOAA HMS smoke polygons; also build coverage and fixed-site sensitivity metrics |
| `process_mtbs.py`, `process_canada.py` | Build U.S. MTBS and Canadian NBAC burned-area series |
| `process_historical_smoke_evidence.py` | Validate normalized events, observations, and citations; build the 672-month search ledger and NOAA candidate index |
| `process_event_history.py` | Normalize large-fire records, derive the legacy documentary event export, annual fire context, and modeled state burden |
| `process_all_fire_history.py`, `process_fire_history.py` | Build the source-covered 1950–2026 fire catalog and 1992–2020 density grid |
| `process_current_fire_activity.py` | Build the July 18, 2026 U.S./Canada YTD fire snapshot |
| `build_dashboard.py` | Assemble the canonical website contract in `data/processed/dashboard.json` |
| `validate.py` | Write the 2021 Stanford/O'Dell comparison report |
| `render_social_graphics.py` | Render ten 2400×1350 publication graphics from the dashboard contract |

`run_all.py` executes these stages in dependency order and refreshes the processed-file inventory last.

## Exposure metric

Let `s(g,d)` be the modeled wildfire-attributable PM2.5 increment for geography `g` on day `d`, and `P2020(g)` its fixed July 1, 2020 population.

The threshold is `T = 35.5 µg/m³`, the lower PM2.5 concentration breakpoint for AQI 101. Because AQI is defined from total pollutant concentration, the report calls this an **AQI-101-equivalent wildfire-smoke increment**, not a literal wildfire AQI.

Daily qualifying population:

`H(d) = sum_g P2020(g) × I[s(g,d) >= T]`

A widespread smoke day has `H(d) >= 10,000,000`.

Annual outputs include:

- widespread smoke days;
- population-days above the threshold;
- peak daily population and date;
- fixed residents exposed at least once;
- threshold and population-cutoff sensitivity metrics.

The comparable series fixes population at 2020 levels so changes in the chart reflect modeled smoke exposure rather than population growth.

## Implemented data products

### Stanford ECHO, 2006–2023

The headline series aggregates Stanford ECHO v2 beta daily county wildfire-smoke PM2.5 estimates. Stanford combines regulatory monitors, NOAA satellite smoke maps, and satellite, fire, weather, and land predictors. This repository aggregates the released county estimates; it does not claim to reproduce Stanford's model training.

The series begins in 2006, the first complete year of NOAA's national daily HMS smoke archive. Pre-2006 episodes are displayed only as documented historical context.

### O'Dell/Ford validation, 2021

The local validation uses the released daily 15 km median-background grid. Each Census ZCTA internal point is assigned to its nearest valid grid center. Smoke enhancement is `PM25 - Background_PM25` on HMS-overhead days.

The join covers 32,462 CONUS/DC ZCTAs containing 328,334,009 residents, or 99.72% of the reference population. It is a point-to-grid sensitivity check, not an area-weighted ZCTA estimate and not a continuation of the Stanford line.

The published O'Dell/Ford Dryad v5 release includes recommended mean-background grids for 2006–2024. `process_odell_extension.py` aggregates the released grids without recreating the publisher's private model inputs: it verifies the archive checksum, extracts one annual netCDF into an auto-deleted temporary directory, and writes independent ZCTA, daily, and annual outputs. The standalone 2024 file is 317 MB, but Dryad returned HTTP 403/401 to automated retrieval from the release environment; the 2006–2023 mean archive is 5.71 GB and remains an optional pinned input on storage-constrained machines. Use `python -m pipeline.run_all --odell-extension` after placing either verified archive in `sources/odell-ford/dryad-v5/downloads/`.

### Monitor-plus-satellite screen, 2006–2026

A qualifying monitor-day has observed **total** PM2.5 at or above 35.5 µg/m³ and a monitor point inside a NOAA HMS smoke polygon. The pipeline applies that screen to every calendar year from 2006 onward, writes complete annual rows through 2025, and writes a Jan 1–July 18 comparison for every year through 2026. The 2026 record combines AQS through May 31 with preliminary AirNow `PM2.5-24hr` site-days from June 1 through July 18.

EPA daily files repeat summaries when exceptional-event observations are included or excluded. The processor retains `Included` rows and ignores `Excluded` variants, preventing high smoke observations from being silently removed. The bulk daily files do not expose the specific RF Canadian-fire, RT U.S.-wildfire, or RM prescribed-fire qualifier codes; HMS overlap supplies smoke presence but not fire origin.

County population provides an indicative scale. This product does not subtract non-fire pollution or estimate smoke in unmonitored areas, so its rows carry `comparable_to_stanford=false` and remain visually separate. Annual monitor/site/county/population coverage and a fixed panel of sites with at least 75% valid days in every 2006–2025 year make network change inspectable. The fixed panel is a sensitivity analysis, not a correction for unmonitored population.

### Fire activity and incident records

- U.S. burned area uses MTBS mapped wildfires from 1984 onward.
- Canadian burned area uses NBAC adjusted annual area from 1972–2025.
- The all-fire catalog uses U.S. FPA FOD for 1992–2020, NIFC InFORM for 2021–2026, and Canadian NFDB records for 1950–2025.
- July 18, 2026 fire totals come from NIFC IMSR and NRCan CWFIF and are labeled preliminary YTD observations.

Fire counts and acres are context for smoke-generation potential. They are not exposure estimates, and records from different archives or countries are not merged into one incidence trend.

## Validation

The release test suite enforces:

- unique source IDs and complete provenance fields;
- local source-file integrity where snapshots are retained;
- expected calendar coverage and null-not-zero behavior for uncovered history;
- unique geographic/date grains and reconciliation across daily, annual, state, and incident tables;
- threshold behavior at the 35.5 µg/m³ boundary;
- population coverage, coordinates, units, and source-era separation;
- 2026 partial-year labels and identical Jan 1–July 18 comparison windows;
- explicit non-comparability between Stanford, O'Dell/Ford, operational smoke, and fire records;
- reproducible social graphics and rendered website data contracts.

The Python suite covers pipeline contracts, source receipts, data reconciliation, and the storage-bounded O'Dell processor. The website adds rendered HTML, downloadable-file, accessibility, and Open Graph checks.

## Outputs

- [`../data/README.md`](../data/README.md) defines every processed table and field boundary.
- [`../sources/README.md`](../sources/README.md) records source selection, licensing, and model-replication boundaries.
- [`../sources/manifest.json`](../sources/manifest.json) is the machine-readable source and research-paper index.
