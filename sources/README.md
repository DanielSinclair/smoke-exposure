# Sources and provenance

This directory is the single home for provider inputs, frozen receipts, source evaluations, and research citations. The machine-readable catalog is [`manifest.json`](manifest.json); generated analytical tables live in [`../data/processed/`](../data/processed/).

The release uses a common operational cutoff of **July 18, 2026**. A July 19 availability audit is retained because that day's AirNow coverage was incomplete and the matching NIFC situation report was unavailable.

## Source-owned snapshots

- [`census/2020/`](census/2020/) — fixed county/ZCTA population and geography
- `stanford-echo/v2-beta/` — ignored Stanford ECHO download cache
- `odell-ford/2021/` — ignored O'Dell/Ford download and working cache
- [`epa-aqs/daily-pm25-2006-2026/receipt.json`](epa-aqs/daily-pm25-2006-2026/receipt.json) — exact EPA AQS PM2.5 annual files for the complete monitor screen
- [`current-2026-receipt.json`](current-2026-receipt.json) — AirNow, NIFC, and NRCan operational inputs through July 18
- [`current-2026-availability-audit.json`](current-2026-availability-audit.json) — rejected partial July 19 national update
- [`noaa-hms/annual-smoke-polygons-2006-2026/receipt.json`](noaa-hms/annual-smoke-polygons-2006-2026/receipt.json) — exact NOAA HMS annual smoke-polygon files
- [`odell-ford/dryad-v5/receipt.json`](odell-ford/dryad-v5/receipt.json) — Dryad v5 file IDs, sizes, checksums, local paths, and the current download-access/storage blockers; archives remain ignored and are processed one annual netCDF at a time
- [`nifc/2026/`](nifc/2026/) and [`nrcan-cwfif/2026/`](nrcan-cwfif/2026/) — current fire-activity snapshots
- [`mtbs/`](mtbs/), `usfs-fpa-fod/`, and [`nifc-inform/`](nifc-inform/) — U.S. fire records
- [`nrcan-nbac/`](nrcan-nbac/) and [`nrcan-nfdb/`](nrcan-nfdb/) — Canadian burned-area and fire records
- [`usa-today/`](usa-today/) and [`event-context/`](event-context/) — preserved article values and source-backed event leads
- [`historical-smoke-evidence/v1/`](historical-smoke-evidence/v1/) — normalized documentary events, observations, and original-source citations
- [`noaa-storm-events/1950-2005/receipt.json`](noaa-storm-events/1950-2005/receipt.json) — exact NOAA annual detail files used for the historical wildfire candidate screen

Large provider downloads remain ignored. The manifest records the exact publisher, release, path, coverage, role, and license needed to retrieve them.

## Controlling source decisions

| Source | Coverage | Release role |
| --- | --- | --- |
| Stanford ECHO v2 beta | Daily county smoke PM2.5, 2006–2023 | Headline comparable exposure series |
| O'Dell/Ford Dryad v5 | Daily 15 km smoke/non-smoke PM2.5, 2006–2024 | Independent published model; standalone 2024 and optional 5.71 GB 2006–2023 mean-background archives are pinned separately |
| U.S. Census Bureau | 2020 county and ZCTA population/geography | Fixed exposure denominator and local geography |
| EPA AQS | Regulatory monitor-day total PM2.5 | Consistent annual observation screen, 2006–May 31, 2026 |
| EPA AirNow | Preliminary operational monitor-day total PM2.5 | June 1–July 18, 2026 supplement |
| NOAA HMS | Daily analyst-drawn smoke polygons, 2005–present | Smoke-presence screen; first complete comparison year is 2006 |
| NOAA NCEI ISD | Global hourly weather observations, 1901–present | Historical smoke/weather context only; not PM2.5 exposure |
| NOAA Storm Events | Annual event details, 1950–2005 snapshot | Wildfire incident candidates and narrative keyword screen; the Wildfire type begins in 1996 and is not a smoke census |
| MTBS | Mapped U.S. large fires, 1984–2026 | U.S. burned area and large-fire context; recent years provisional |
| USFS FPA FOD | U.S. reported wildfire occurrences, 1992–2020 | Comprehensive historical U.S. incident lane |
| NIFC InFORM | Public U.S. fire occurrences, 2021–2026 snapshot | Revisionable current U.S. incident lane |
| NRCan NBAC | Canadian adjusted burned area, 1972–2025 | Complete annual Canadian burned-area series |
| NRCan NFDB | Canadian reported fire points, 1950–2025 | Source-covered Canadian incident lane; completeness varies by agency/year |
| NIFC IMSR / NRCan CWFIF | 2026 YTD national totals through July 18 | Separate current fire-activity snapshot |

## Model and historical boundaries

Stanford v2 publishes daily estimates but not its complete training pipeline. The data page labels the release beta/preliminary. This repository aggregates the published county-day file and does not claim an exact model rebuild.

The pre-2006 historical evidence catalog is a separate documentary product. Its three-table source contract stores interpreted events, source-specific observations, and citations independently. Every accepted event has at least one observation and one original source; evidence levels, attribution confidence, affected U.S. geography, and quantitative availability are explicit. All rows are `quantitatively_comparable=false`.

The monthly search ledger covers all 672 months from 1950 through 2005. A blank month is either `not_systematically_reviewed` or `candidate_screen_complete_not_exhaustive`; neither means no smoke. NOAA Storm Events contributes 2,236 Wildfire records from 1996–2005 as candidates or corroboration. Changing event-type coverage and free-text reporting prevent its use as a historical exposure trend.

Stanford v1 has public code and data for 2006–2020, but it is a different model version. O'Dell/Ford publishes 2006–2024 released grids and method code, but its model-building scripts still reference private WRF grid assets and omitted HMS preprocessing. This project therefore aggregates the released grids rather than claiming to recreate them from raw monitors. The mean-background 2006–2023 archive is 5,707,923,964 bytes; it is checksum-pinned but intentionally not downloaded on the storage-constrained release workstation. The processor is complete and streaming: once that archive is placed under `sources/odell-ford/dryad-v5/downloads/`, it extracts and deletes one annual netCDF at a time.

No national daily record combines PM2.5, smoke attribution, stable spatial coverage, and population exposure from 1950 to the present. Weather observations, TSP, PM10, IMPROVE, and early AQS each cover different pollutants, places, or periods. Pre-2006 smoke episodes remain documented context, and years without comparable data are never filled with zero.

Canadian NBAC is a homogeneous adjusted burned-area product from 1972 onward. Earlier Canadian NFDB points are retained as incident records, not appended to NBAC as an equivalent annual area series. U.S. MTBS, FPA FOD, and InFORM also retain their separate source-era labels.

## Supplemental sources reviewed

| Source | Decision |
| --- | --- |
| PurpleAir | Useful for dense recent local checks after correction and QA; not used in the national historical series because the network begins in 2016, changes over time, and has redistribution constraints |
| IQAir | Used only for air-quality context; public historical depth and proprietary methods are insufficient for a reproducible national backbone |
| OpenAQ | Discovery and cross-check service only; U.S. records resolve back to original EPA or sensor providers |
| Sensor.Community | Exploratory local sensor archive; not used in released metrics |
| Ambee / Tomorrow.io | Proprietary products without a frozen, redistribution-ready national input; not used |

## Research and event context

The manifest lists eight research and methodology papers, including the Stanford v1 paper, Stanford v2 preprint, O'Dell/Ford method paper, national U.S. smoke-trend studies, the 2023 Canadian transboundary-smoke analysis, the 2026 GeoHealth paper, and the 1950 Great Smoke Pall report.

User-supplied reporting and social posts are retained as event/context leads:

- [USA Today wildfire graphics](https://www.usatoday.com/story/graphics/2026/07/16/wildfires-data-damage-historical-graphs/90861203007/) led back to MTBS.
- [Ben Noll's Canadian fire-season graphic](https://x.com/BenNollWeather/status/2078451048486961519) and the [Washington Post July 18 report](https://www.washingtonpost.com/weather/2026/07/18/thick-wildfire-smoke-lingers-over-mid-atlantic-early-saturday/) led back to NRCan fire records, ERA5 context, NOAA, and EPA observations.
- [Robert Rohde's July 18 map](https://x.com/RARohde/status/2078548604969447552) led back to official CWFIS active-fire and peak-smoke services.

News and social posts document episodes and analytical leads. Reproduced values use the primary government or research dataset wherever available.

## Licensing

Each manifest record carries the publisher's license or the absence of an explicit license. U.S. federal datasets are generally public domain; Census, EPA, NOAA, NIFC, and USFS attribution is preserved. Canadian products follow the Open Government Licence–Canada and source-agency terms. Stanford beta data and context reporting retain their publisher restrictions and are not republished beyond permitted derived outputs.

Project code is licensed separately under the repository's [MIT License](../LICENSE).
