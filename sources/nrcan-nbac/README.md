# Canadian NBAC source

This directory contains the Natural Resources Canada / Canadian Forest Service National Burned Area Composite used for Canadian fire-activity context.

## Production dataset

| Field | Value |
| --- | --- |
| Dataset | National Burned Area Composite (NBAC) annual summary |
| Publisher | Natural Resources Canada, Canadian Forest Service |
| Grain | One Canada-wide adjusted burned-area total per fire year |
| Coverage | 1972–2025, 54 annual observations |
| Version | `20260513` |
| Retrieved | 2026-07-18 |
| Source page | <https://cwfis.cfs.nrcan.gc.ca/ha/nfdb?type=nbac&year=9999> |
| Exact workbook | <https://cwfis.cfs.nrcan.gc.ca/downloads/nbac/NBAC_summarystats_1972_to_2025_20260513.xlsx> |
| License | [Open Government Licence–Canada](https://open.canada.ca/en/open-government-licence-canada) |

The pipeline reads the `CANADA` column from the `sumstats_admin_name` worksheet, whose title identifies adjusted hectares. Hectares are converted to international acres using `1 ha = 2.471053814671653 acres`.

```bash
.venv/bin/python -m pipeline.process_canada
.venv/bin/python -m unittest pipeline.tests.test_canada -v
```

The generated file is [`../../data/processed/canada_fire_annual.csv`](../../data/processed/canada_fire_annual.csv). Rows are complete annual observations in this release but remain revisionable as NRCan updates historical mapping.

## Product boundary

NBAC is the national adjusted burned-area composite produced annually from 1972 onward. Earlier Canadian NFDB point records use different reporting and mapping systems, so the pipeline does not append them to NBAC as one homogeneous area series.

The workbook supplies adjusted burned area, not a comparable national ignition count. `fire_count` is therefore blank in the output. NFDB agency reports remain available in the separately labeled incident catalog.

The complete NBAC release ends in 2025. The July 18, 2026 CWFIF total is an active-season YTD observation and appears only in the separate current-fire table.

## Source trace

- [Ben Noll's July 18 graphic](https://x.com/BenNollWeather/status/2078451048486961519) and the related [Washington Post article](https://www.washingtonpost.com/weather/2026/07/18/thick-wildfire-smoke-lingers-over-mid-atlantic-early-saturday/) identify CNFDB/NBAC and ERA5 as their fire/climate sources.
- [Robert Rohde's July 18 active-fire/smoke map](https://x.com/RARohde/status/2078548604969447552) identifies CWFIS current layers. It is event context, not a complete annual burned-area observation.
- [Hausfather's reproducible analysis](https://github.com/hausfath/canada-wildfires-climate) uses the same 1972-forward NBAC boundary. This project reads the official NRCan workbook directly.

## References

- [CWFIS Canadian National Fire Database / NBAC](https://cwfis.cfs.nrcan.gc.ca/ha/nfdb?type=nbac&year=9999)
- [CWFIS FAQ](https://cwfis.cfs.nrcan.gc.ca/en/faq)
- [NRCan Fire Monitoring, Accounting and Reporting System](https://natural-resources.canada.ca/forests-forestry/wildland-fires/fire-monitoring-accounting-reporting-system)
- [NBAC generation paper](https://doi.org/10.3390/rs12172771)
- [1972 extension paper](https://doi.org/10.3390/rs14133050)
