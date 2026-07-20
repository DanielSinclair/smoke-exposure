# Processed data products

This directory owns generated, reviewable analytical outputs. Source inputs and provenance live only in provider-labeled directories under [`sources/`](../sources/); transformation code and tests live in [`pipeline/`](../pipeline/).

## Product dictionary

| File | Grain and role |
| --- | --- |
| `stanford_daily_smoke_2006_2023.csv` | One U.S. date from Stanford ECHO v2 beta county-day wildfire-smoke PM2.5, using fixed July 1, 2020 county populations |
| `stanford_annual_smoke_2006_2023.csv` | One year; controlling comparable series for broad days, population-days, peak exposure, and residents exposed |
| `stanford_metric_sensitivity_2006_2023.csv` | One year across alternative PM2.5 and population thresholds |
| `stanford_aggregation_audit.json` | Parsed-row, coverage, population, and threshold audit for the Stanford aggregation |
| `zcta_2020.csv` | One 2020 Census ZCTA with population, coordinates, state assignment, and land area |
| `zcta_smoke_exposure_2021.csv` | One CONUS/DC ZCTA mapped to the nearest released O'Dell/Ford grid center |
| `zcta_smoke_daily_national_2021.csv` | One date from the independent 2021 ZCTA reconstruction |
| `smoke_annual_2021.csv` | One-row annual summary of the 2021 ZCTA reconstruction |
| `validation_report.json`, `.md` | Stanford/O'Dell 2021 overlap and spatial-coverage diagnostics |
| `operational_smoke_screen_daily_2006_2026.csv` | One date from the total-PM2.5 plus HMS monitor-coincidence screen, including event-policy and fixed-site sensitivity fields |
| `operational_smoke_screen_annual_2006_2026.csv` | Complete annual monitor-screen summaries through 2025 and a provisional 2026 row through July 18 |
| `operational_smoke_screen_same_cutoff_2006_2026.csv` | One Jan 1–July 18 comparison window for every year, 2006–2026 |
| `operational_smoke_screen_monitor_coverage_2006_2026.csv` | Annual site, county, state/DC, site-day, population-footprint, HMS, and balanced-panel coverage diagnostics |
| `operational_smoke_screen_audit_2006_2026.json` | AQS event handling, source cutoffs, balanced-panel definition, and non-comparability contract |
| `operational_smoke_proxy_daily_2024_2026.csv` | One date from the separate observed total-PM2.5 plus HMS monitor-coincidence screen |
| `operational_smoke_proxy_annual_2024_2026.csv` | One year/snapshot of operational proxy totals; 2026 is a provisional AQS/AirNow composite through 2026-07-18 |
| `current_fire_activity_2026.csv` | Two provisional 2026 YTD rows: U.S. NIFC and Canadian NRCan CWFIF counts and burned area through 2026-07-18 |
| `mtbs_wildfires_annual.csv` | One ignition year of mapped U.S. wildfires; count and acres burned |
| `canada_fire_annual.csv` | One Canadian fire year, 1972–2025, from NBAC adjusted burned area; homogeneous fire counts intentionally blank |
| `large_fire_incidents_source_covered.csv` | One eligible source record from the MTBS wildfire or CNFDB greater-than-200-hectare archive; 38,247 records, with source IDs and completeness flags |
| `large_fire_incidents_annual_source_covered.csv` | One year and country rolled up from the normalized incident table; explicitly not comparable across countries |
| `all_fire_incidents_annual_source_covered.csv` | Country-year rollups from 2.3 million U.S. FPA FOD reports (1992–2020) and the full Canadian NFDB point archive (1950–2025); source coverage remains separate |
| `fire_incidents_monthly_source_covered.csv` | Every country-month from 1950–2026 with nullable counts and recorded acres from one designated source lane; blanks are uncovered, not zero |
| `fire_incidents_annual_catalog_1950_2026.csv` | Annual reconciliation of the monthly incident catalog, including records whose source date lacks a usable month |
| `fire_incident_catalog_sources.csv` | Exact source, scope, coverage tier and non-comparability rule controlling each country-year lane |
| `all_fire_density_tiles_1992_2020.csv` | Fixed 30×24 North America grid of comprehensive reported-fire counts and acres during the shared 1992–2020 period |
| `fire_year_context.csv` | Up to three largest named or identified large-fire records per year and country; tooltip context only, never causal smoke attribution |
| `smoke_region_context_2006_2023.csv` | One affected state-year in the comparable Stanford series, ranked within year by high-smoke population-days at the same 35.5 µg/m³ threshold |
| `historical_smoke_events_1950_2005.csv` | One reviewed documentary U.S. wildfire-smoke episode with evidence level, attribution confidence, affected geography, and source keys |
| `historical_smoke_observations_1950_2005.csv` | One source-specific observation supporting an interpreted historical event |
| `historical_smoke_sources.csv` | One original government or published citation used by the event and observation tables |
| `historical_smoke_search_coverage_1950_2005.csv` | Every month from 1950–2005 with explicit search status; unknown and screened-without-a-case are never encoded as zero smoke |
| `noaa_storm_events_wildfire_candidates_1950_2005.csv` | NOAA Wildfire event records from 1996–2005 with smoke/haze narrative signals; candidate context only |
| `documented_smoke_episodes_1950_2005.csv` | Backward-compatible site export derived from the normalized historical evidence tables |
| `dashboard.json` | Canonical compact contract consumed by the one-page website; includes every-year Jan 1–July 18 smoke comparisons and 30×24 reported-fire density tiles |

### Optional O'Dell/Ford extension outputs

`pipeline.process_odell_extension` writes `odell_zcta_exposure_released_years.csv.gz`, `odell_smoke_daily_released_years.csv`, `odell_smoke_annual_released_years.csv`, and `odell_processing_audit.json` for every checksum-verified Dryad v5 mean-background archive available locally. These outputs are not checked into this release because Dryad rejected automated retrieval of the standalone 2024 file from the release environment and the 2006–2023 mean archive is 5.71 GB. [`../sources/odell-ford/dryad-v5/receipt.json`](../sources/odell-ford/dryad-v5/receipt.json) records the exact file IDs, checksums, paths, and retry instructions. The processor is covered by a synthetic full-year netCDF unit test and never fabricates missing years.

## Metric boundary

The historical fire calendar is an evidence catalog, not a continuous incidence trend. It never sums U.S. and Canadian records, never unions overlapping archives, and never treats a reported fire as proof of U.S. smoke exposure. Canadian NFDB reporting varies by agency and year; U.S. MTBS is large-fire-only before the FPA FOD era; InFORM is a revisionable public-record snapshot rather than an official annual count. Its independent smoke dimensions remain null before the comparable model period.

The historical smoke catalog is also not a continuous incidence trend. Evidence levels run from 1 (one authoritative documentary source) through 4 (instrumented PM2.5/AQI or atmospheric analysis with defensible attribution). They describe evidence strength, not smoke severity. Source-fire attribution is separately labeled `confirmed`, `probable`, `possible`, or `unknown`. A documented case may be local or regional; no population reach is inferred from the affected-region text.

For the comparable Stanford series, a high-smoke geography-day has wildfire-attributable PM2.5 at least **35.5 µg/m³**. A broad day has at least **10 million fixed-2020 residents** across qualifying counties. Population-days sum daily qualifying residents.

The 2021 ZCTA reconstruction uses `PM25 - Background_PM25` only on HMS-overhead days. The released background is a seasonal median of no-smoke days. It thresholds the grid value nearest each ZCTA internal point; it is neither an area-weighted ZCTA average nor an input to the Stanford line.

The 2006–2026 operational screen has a different estimand: a valid monitor-day with **observed total PM2.5** at or above 35.5 µg/m³ whose monitor point lies inside a NOAA HMS smoke polygon. Complete calendar-year summaries are available through 2025, and every year also has a Jan 1–July 18 comparison window. The 2026 snapshot uses AQS through May 31 and preliminary EPA AirNow `PM2.5-24hr` site-days from June 1 through July 18. A county is counted once per date when at least one monitor qualifies, and its 2020 population is an indicative scale. That does not establish that every county resident was exposed, subtract non-fire pollution, or identify the fire's country of origin. Its rows carry `comparable_to_stanford=false`.

The AQS event columns preserve event-affected measurements by using `Included` summaries and excluding alternate `Excluded` summaries. Eight physical site-days across 2015, 2017, 2018, and 2023 have an excluded variant without a usable included/no-event counterpart; they remain absent and are counted in the audit rather than substituted with the event-excluded concentration. The bulk daily files do not expose RF/RT/RM fire qualifier codes, so those codes are not inferred. The fixed-site columns restrict results to monitors with at least 75% valid days in every year from 2006 through 2025; they measure sensitivity to network churn, not national population exposure.

For completed historical HMS annual bundles, `hms_data_through` is December 31 even when the last day containing a drawn smoke polygon is earlier. `hms_last_polygon_date` preserves that distinction: a day with no polygon is a valid no-coincidence screen day, not a missing archive day. The current-year bundle remains bounded by its latest available polygon date.

The current fire table is also separate from the historical series. NIFC reported **40,357 fires and 3,853,513 acres** in the U.S.; NRCan CWFIF reported **3,815 fires and 2,914,550.7 hectares (7,202,012 acres)** in Canada as of July 18, 2026. Both are preliminary YTD operational totals. They are not full-year observations and are not method-comparable to the MTBS large-fire or NBAC adjusted-area histories.

`dashboard.json.smoke_same_cutoff` puts every year from 2006 through 2026 on the same Jan 1–July 18 calendar window in two separate lanes. One lane is Stanford modeled smoke PM2.5 for 2006–2023. The other applies the AQS/HMS observed screen across 2006–2026 and includes a 117-site fixed-panel sensitivity; 2026 supplements lagged AQS with preliminary AirNow. The lanes use independent scales and are never joined into one estimator.

`dashboard.json.fire_density_tiles` bins georeferenced U.S. FPA FOD and Canadian NFDB fire reports into a fixed 30×24 North America grid over their shared 1992–2020 window. Six reproducible burned-acre bands use the 10th, 25th, 50th, 75th and 90th percentiles of occupied cells; `dashboard.json.fire_density_scale` publishes the exact thresholds and concentration statistic used by the site. Hover values retain exact incident counts, acres, regions and source IDs. It is a spatial context figure, not a harmonized U.S.–Canada incidence comparison; the two source products use different reporting systems and coverage.

`fire_year_context.csv` is intentionally descriptive rather than attributive. It selects the largest records with reported names (falling back to agency incident IDs when necessary) from MTBS and the Canadian National Fire Database. A fire appearing beside a year's smoke metric means only that it occurred in that year; the project has not linked its plume to the exposed counties. `smoke_region_context_2006_2023.csv`, by contrast, is calculated from the Stanford county estimates themselves and therefore can identify the states carrying the most modeled burden, but not the fire or country that produced the smoke.

## Source-covered large-fire record dictionary

`large_fire_incidents_source_covered.csv` is comprehensive only within its two named source products. It is not a census of every fire. The U.S. rows are MTBS records classified as wildfire; MTBS maps fires of at least 500 acres in the East or 1,000 acres in the West. The Canadian rows are non-prescribed records in NRCan's large-fire point archive, which includes reported fires greater than 200 hectares. NRCan warns that contributed data are incomplete, may contain errors, and vary by agency and year.

| Field | Meaning |
| --- | --- |
| `normalized_record_id` | Pipeline-unique key: MTBS fire ID or stable CNFDB archive-row identifier |
| `incident_name`, `label_kind` | Reported fire name when present; otherwise the agency incident ID and an explicit fallback flag |
| `source_record_id`, `agency_incident_id` | Original source identifiers retained for audit; CNFDB's constructed ID is not always unique when an agency ID is unavailable |
| `year`, `geography`, `region` | Source-reported calendar year, country, and state/province/territory or Parks Canada source region |
| `latitude`, `longitude` | Source coordinates rounded to five decimals; questionable locations are retained rather than silently dropped |
| `location_plausible_for_geography` | Coarse range check only, not a corrected location or accuracy guarantee |
| `acres` | Source area converted to whole acres; Canadian hectares use 2.4710538147 acres per hectare |
| `coverage_scope` | Source-specific large-fire inclusion rule |
| `source_year_status`, `source_coverage_complete`, `provisional` | Completeness/revision boundary. Canadian rows remain incomplete-by-definition because coverage varies by agency/year; MTBS 2025–2026 rows are provisional |
| `source_release`, `source_dataset` | Frozen source version and publisher dataset |
| `causal_smoke_attribution` | Always `false`; incident co-occurrence in a year does not prove that its smoke caused modeled exposure |

The annual source-covered rollup sums records and acres from this table without harmonizing the two coverage rules. `comparable_to_other_geography=false` prevents the MTBS and CNFDB counts from being interpreted as a country ranking. `fire_year_context.csv` is a three-record display subset and every row reconciles by `normalized_record_id` to the full table.

## Coverage checks

The 2021 grid join covers 32,462 CONUS/DC ZCTAs containing 328,334,009 people—99.72% of the 2020 Census CONUS/DC resident total. Mean nearest-grid distance is 6.188 km; p95 is 9.712 km, p99 is 10.686 km, maximum is 54.287 km, and 16 ZCTAs exceed 20 km. The annual comparison is explicitly `PASS_FOR_2021_DEMO_WITH_LIMITATIONS`:

- O'Dell/ZCTA: 4 broad days, 232,320,924 population-days, peak 36,819,622.
- Stanford/county: 3 broad days, 216,184,000 population-days, peak 29,447,000.
- Differences: +1 day, +7.46% population-days, +25.04% peak population.

The smoke grid is CONUS; DC is included and Alaska, Hawaii, Puerto Rico, territories, and unassigned records are excluded from exposure calculations. The national ZCTA dimension remains national.
