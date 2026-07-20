# U.S. Wildfire Smoke Exposure Trend

A source-backed report on U.S. wildfire-smoke exposure and North American fire activity.

[View the report](https://danielsinclair.github.io/smoke-exposure/)

## Scope

The primary series uses Stanford ECHO daily county estimates from 2006–2023. A qualifying day has modeled wildfire-smoke PM2.5 of at least **35.5 µg/m³** (AQI 101) in counties containing **10 million or more residents**. Population-days sum the residents exposed on every qualifying day using fixed 2020 Census population.

The report keeps unlike evidence separate:

- Comparable modeled exposure, 2006–2023
- AQS/HMS monitor and satellite checks, 2006–2026
- Documented historical smoke episodes, 1950–2005
- U.S. and Canadian fire records and burned area

The preliminary 2026 data ends July 18. Earlier smoke episodes are evidence, not equivalent exposure estimates or assumed zeros.

## Architecture

The Python pipeline downloads the files listed in [`sources/manifest.json`](sources/manifest.json), normalizes smoke, population, and fire records, then writes the site contract to [`data/processed/dashboard.json`](data/processed/dashboard.json). Unit tests check the calculations and generated tables.

The site is a React and TypeScript report built with Next.js, Vinext, and Vite. Custom SVG charts use accessible, Safari-compatible tooltips. Project CSS applies [Kami](https://github.com/tw93/Kami)'s editorial layout and print conventions; Kami is not a runtime dependency. GitHub Actions publishes a static, base-path-aware GitHub Pages build.

Key directories: [`sources/`](sources/), [`pipeline/`](pipeline/), [`data/processed/`](data/processed/), and [`site/`](site/).

## Data

- [Stanford ECHO wildfire-smoke PM2.5](https://www.stanfordecholab.com/wildfire_smoke)
- [O'Dell/Ford smoke and non-smoke PM2.5](https://doi.org/10.5061/dryad.k0p2ngfhv)
- [U.S. Census population and ZCTA geography](https://data.census.gov/table/DECENNIALDHC2020.P1?g=010XX00US%248600000)
- [EPA AQS](https://aqs.epa.gov/aqsweb/airdata/download_files.html), [AirNow](https://files.airnowtech.org/airnow/docs/DailyDataFactSheet.pdf), and [NOAA HMS](https://www.ospo.noaa.gov/products/land/hms.html)
- [MTBS](https://www.mtbs.gov/), [USFS FPA FOD](https://doi.org/10.2737/RDS-2013-0009.6), and [NIFC InFORM](https://www.arcgis.com/home/item.html?id=60a94840152b4a89bec467a9f052f135)
- [Canadian NBAC and NFDB](https://cwfis.cfs.nrcan.gc.ca/ha/nfdb)

The [source catalog](sources/README.md) lists the original publications, direct downloads, licenses, and suitability notes.

## Rebuild

Use Python 3.11+ and Node.js 22.13+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r pipeline/requirements.txt
.venv/bin/python -m pipeline.run_all --download
.venv/bin/python -m unittest discover -s pipeline/tests -v

cd site
npm ci
npm run typecheck
npm run lint
npm test
npm run build:pages
```

Later rebuilds can omit `--download`. See [`pipeline/README.md`](pipeline/README.md) for formulas and [`data/README.md`](data/README.md) for generated fields.

## License

Code is [MIT licensed](LICENSE). Source data retains the licenses recorded in [`sources/manifest.json`](sources/manifest.json).
