# U.S. Wildfire Smoke Exposure Trend website

The React/TypeScript one-page report for the wildfire-smoke data pipeline.

## Local development

Requires Node.js 22.13+.

```bash
npm ci
npm run dev
```

Validation and production builds:

```bash
npm run typecheck
npm run lint
npm test
npm run build:pages
```

`npm run sync-data` copies the canonical processed tables and source manifest into ignored build-time files under `public/data/`. Generated website copies are not committed twice.

## Data contract

The page reads `public/data/dashboard.json`, generated from [`../data/processed/dashboard.json`](../data/processed/dashboard.json). Its principal sections are:

- `annual_smoke` and `smoke_trend` — Stanford modeled exposure, 2006–2023;
- `smoke_history` — documented historical episodes, modeled exposure, and recent operational evidence on one calendar grid with explicit source-era states;
- `operational_proxy` and `operational_same_cutoff` — recent 2024–2026 monitor-plus-satellite evidence;
- `smoke_same_cutoff` — two independent Jan 1–July 18 lanes: Stanford 2006–2023 and the observed AQS/HMS screen 2006–2026;
- `current_fire_activity` — July 18, 2026 NIFC and NRCan YTD snapshots;
- `annual_fire` and `annual_canada_fire` — U.S. MTBS and Canadian NBAC burned area;
- `fire_incident_catalog`, `fire_density_tiles`, and `fire_year_context` — source-covered fire history and tooltip context;
- `smoke_region_context` — modeled state-level burden for 2006–2023;
- `sources` and `research_papers` — original-publisher links, direct data links, and citations.

The Stanford, O'Dell/Ford, monitor-plus-satellite, and fire-activity products are never rendered as one continuous estimator.

## Interface

The report adapts the MIT-licensed [Kami](https://github.com/tw93/Kami) equity-report structure into a narrow data paper. It uses responsive line charts, calendar matrices, fire-density cells, keyboard-accessible tooltips, selectable detail panels, and printer-safe A4 styling.

Ink blue identifies Canadian series where U.S. and Canadian values share a figure. Official EPA category colors appear only in AQI context. All other visual encoding remains monochromatic.

The header's **Print / save PDF** control opens the browser print dialog. Print styles hide interactive controls and the source appendix, preserve chart colors, and paginate the report cleanly.

Ten source-backed 2400×1350 share graphics are generated into [`public/social/`](public/social/) from the same dashboard contract.

## Deployment

`npm run build:pages` exports the static site to `pages-dist/`. [GitHub Actions](../.github/workflows/pages.yml) publishes that artifact from `main` to [danielsinclair.github.io/smoke-exposure](https://danielsinclair.github.io/smoke-exposure/).
