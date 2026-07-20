import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the one-page wildfire data report", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>U\.S\. Wildfire Smoke Exposure Trend/);
  assert.match(html, /Modeling wildfire smoke air quality impact trendline/);
  assert.match(html, /How wildfire smoke exposure has changed/);
  assert.match(html, /47%/);
  assert.match(html, /1 → 40/);
  assert.match(html, /1,646/);
  assert.match(html, /1 in 4/);
  assert.match(html, /1\.88B/);
  assert.match(html, /5-year average trend/);
  assert.match(html, /Annual exposure and five-year trend/);
  assert.match(html, /thin gray: individual years/);
  assert.match(html, /blue: trailing five-year average/);
  assert.match(html, /The worst individual smoke days/);
  assert.match(html, /When and where the burden concentrated/);
  assert.match(html, /U\.S\. wildfire-smoke evidence: years with available data/);
  assert.match(html, /Thirty non-contiguous years/);
  assert.match(html, /Documented reports/);
  assert.match(html, /Modeled estimates/);
  assert.match(html, /Recent screen/);
  assert.match(html, /Historical source-review coverage, 1950–2005/);
  assert.match(html, /one square per year/);
  assert.match(html, /Unreviewed years remain unknown rather than zero/);
  assert.match(html, /9\.3(?:<!-- -->)?× higher recent burden/);
  assert.match(html, /documented strength/);
  assert.match(html, /modeled smoke days/);
  assert.match(html, /not yet observed/);
  assert.match(html, /Annual source-covered fire records, 1950–2026/);
  assert.match(html, /within-country count quintiles/);
  assert.match(html, /Hover or focus for series details/);
  assert.match(html, /Comparable modeled smoke-day scale/);
  assert.match(html, /Annual fire-record grayscale/);
  assert.match(html, /What the available evidence says about 2026/);
  assert.match(html, /Same calendar window across all 21 years/);
  assert.match(html, /monitor \+ satellite screen only/);
  assert.match(html, /burden rank/);
  assert.match(html, /peak-reach rank/);
  assert.match(html, /Indicative population-days/);
  assert.match(html, /Peak daily reach/);
  assert.match(html, /days reaching 10M\+/i);
  assert.match(html, /2026 ranks (?:<!-- -->)?2nd(?:<!-- -->)? for cumulative burden and (?:<!-- -->)?2nd(?:<!-- -->)? for peak daily reach/);
  assert.match(html, /population-days exceed 2025 by (?:<!-- -->)?19(?:<!-- -->)?%/);
  assert.match(html, /Canada and United States burned area/);
  assert.match(html, /preliminary smoke and fire updates through (?:<!-- -->)?Jul 18, 2026/);
  assert.match(html, /How the numbers are calculated/);
  assert.match(html, /Input/);
  assert.match(html, /Calculation/);
  assert.match(html, /Output/);
  assert.match(html, /raw\.githubusercontent\.com\/DanielSinclair\/smoke-exposure\/main\/data\/processed\/stanford_daily_smoke_2006_2023\.csv/);
  assert.match(html, /raw\.githubusercontent\.com\/DanielSinclair\/smoke-exposure\/main\/data\/processed\/stanford_annual_smoke_2006_2023\.csv/);
  assert.match(html, /Method terms and caveats/);
  assert.match(html, /3\.85M/);
  assert.match(html, /7\.20M/);
  assert.match(html, /58\.9M/);
  assert.match(html, /AQI 175/);
  assert.match(html, /30th consecutive hour/);
  assert.match(html, /DanielSinclair\/smoke-exposure/);
  assert.match(html, /Sources, papers and downloads/);
  assert.match(html, /Original data sources/);
  assert.match(html, /Research and methodology papers/);
  assert.match(html, /Project data downloads/);
  assert.match(html, /Historical and interpretive context/);
  assert.match(html, /Original source →/);
  assert.match(html, /Direct data ↓/);
  assert.match(html, /Growing wildfire-derived PM2.5 across the contiguous U\.S\./);
  assert.match(html, /Long-range PM2.5 pollution and health impacts from the 2023 Canadian wildfires/);
  assert.match(html, /Health and Regulatory Impacts of PM2.5 From Wildland Fires for 2019-2024/);
  assert.match(html, /machine-readable source manifest/);
  assert.match(html, /Print \/ save PDF/);
  assert.match(html, /property="og:image" content="http:\/\/localhost:3000\/og\.png"/);
  assert.match(html, /name="twitter:card" content="summary_large_image"/);
  assert.match(html, /Ben Noll and Washington Post graphic/);
  assert.match(html, /by <a href="https:\/\/x\.com\/_DanielSinclair"/);
  assert.match(html, /aqi-badge threshold/);
  assert.match(html, /aqi-badge plain/);
  assert.match(html, /<footer class="site-footer">/);
  assert.doesNotMatch(html, /Wildfire smoke is no longer only a western story/);
  assert.doesNotMatch(html, /operational screen|Current smoke screen|Preliminary operational proxy|Daniel Sinclair|The generational question|The honest answer|Sources &amp; provenance/);
  assert.doesNotMatch(html, /Wildfire data paper|Current conditions|Primary navigation|section-number/);
  assert.doesNotMatch(html, /class="takeaways"/);
  assert.doesNotMatch(html, /smoke-bars|area-bar/);
  assert.doesNotMatch(html, /danielsinclair\.me|X · _DanielSinclair|↗|News reports and social posts document episodes/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/);
});

test("keeps hover text selectable and removes references from print", async () => {
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.match(css, /\.floating-panel[\s\S]*?pointer-events: auto;[\s\S]*?user-select: text;/);
  assert.match(css, /\.chart-legend-detail[\s\S]*?cursor: help;/);
  assert.match(css, /\.legend-detail[\s\S]*?cursor: help;/);
  assert.match(css, /\.same-window-kpi[\s\S]*?cursor: help;/);
  assert.match(css, /\.same-window-year[\s\S]*?cursor: crosshair;/);
  assert.match(css, /\.density-scale-detail[\s\S]*?cursor: help;/);
  assert.match(css, /\.history-cell\.evidence-none/);
  assert.match(css, /\.history-cell\.evidence-documentary-1/);
  assert.match(css, /\.history-cell\.evidence-modeled/);
  assert.match(css, /\.history-cell\.evidence-operational/);
  assert.match(css, /\.review-coverage-cell\.level-0/);
  assert.match(css, /\.review-coverage-cell\.level-4/);
  assert.match(css, /@media print[\s\S]*?\.sources-section, \.site-footer \{ display: none !important; \}/);
  const dashboard = await readFile(new URL("../app/Dashboard.tsx", import.meta.url), "utf8");
  assert.match(dashboard, /createPortal\([\s\S]*?document\.body/);
  assert.match(dashboard, /availableBelow >= availableAbove/);
  assert.match(dashboard, /maxHeight: position\.maxHeight/);
  assert.match(dashboard, /onPointerEnter=/);
  assert.match(dashboard, /onPointerOver=/);
  assert.match(dashboard, /onMouseOver=/);
  assert.match(dashboard, /className="chart-legend-detail"/);
  assert.match(dashboard, /className="legend-detail"/);
  assert.match(dashboard, /className="review-coverage-detail"/);
  assert.match(dashboard, /className="same-window-kpi"/);
  assert.match(dashboard, /className=\{`same-window-year/);
  assert.match(dashboard, /className="density-scale-detail"/);
  assert.match(dashboard, /markerMode: "hover"/);
  assert.match(dashboard, /lineWidth: 2\.6/);
  assert.match(dashboard, /color: "#1B365D"/);
  assert.match(dashboard, /color: "#9A4B36"/);
  assert.doesNotMatch(dashboard, /onMouseEnter=/);
});

test("ships a valid dashboard data contract", async () => {
  const raw = await readFile(new URL("../public/data/dashboard.json", import.meta.url), "utf8");
  const data = JSON.parse(raw);
  assert.ok(Array.isArray(data.annual_smoke));
  assert.ok(Array.isArray(data.smoke_history));
  assert.ok(Array.isArray(data.fire_history));
  assert.ok(Array.isArray(data.fire_incident_catalog));
  assert.ok(data.smoke_trend);
  assert.ok(data.extremes);
  assert.ok(data.seasonality);
  assert.ok(data.regional_shift);
  assert.ok(data.fire_smoke_decoupling);
  assert.ok(Array.isArray(data.operational_same_cutoff));
  assert.ok(Array.isArray(data.operational_proxy));
  assert.ok(Array.isArray(data.current_fire_activity));
  assert.ok(Array.isArray(data.annual_fire));
  assert.equal(data.localities, undefined);
  assert.ok(Array.isArray(data.fire_year_context));
  assert.ok(Array.isArray(data.smoke_region_context));
  assert.ok(Array.isArray(data.sources));
  assert.ok(data.sources.length >= 37);
  assert.ok(data.sources.every((source) => source.url.startsWith("https://")));
  assert.ok(data.sources.some((source) => source.id === "census-zcta-gazetteer-2020" && source.retrieval_url));
  assert.ok(Array.isArray(data.research_papers));
  assert.equal(data.research_papers.length, 8);
  assert.ok(data.research_papers.some((paper) => paper.id === "childs-et-al-2025-preprint" && paper.download_url));
  assert.equal(data.meta.smoke_series_start_year, 2006);
  assert.equal(data.meta.smoke_series_end_year, 2023);
  assert.deepEqual(data.smoke_history.map((row) => row.year), Array.from({ length: 77 }, (_, index) => 1950 + index));
  assert.ok(data.smoke_history.every((row) => row.months.length === 12));
  assert.equal(data.documented_smoke_episodes.length, 19);
  assert.equal(data.smoke_history.find((row) => row.year === 1988).months[7].events[0].event_name, "Greater Yellowstone smoke conditions");
  assert.equal(data.smoke_history.find((row) => row.year === 1951).months[0].review_status, "not_reviewed");
  assert.equal(data.smoke_history.find((row) => row.year === 1996).months[0].review_status, "searched_no_qualifying_case_found");
  assert.equal(data.fire_incident_catalog.length, 154);
  assert.equal(data.fire_incident_catalog.find((row) => row.year === 1950 && row.geography === "United States").record_count, null);
  assert.ok(data.fire_incident_catalog.find((row) => row.year === 1950 && row.geography === "Canada").record_count > 0);
  assert.equal(data.smoke_trend.cumulative_population_days, 1_879_266_000);
  assert.equal(data.smoke_trend.early_per_capita_days, 0.08);
  assert.equal(data.smoke_trend.recent_per_capita_days, 0.76);
  assert.equal(data.annual_smoke.find((row) => row.year === 2023).share_exposed_at_least_once, 47.4);
  assert.equal(data.annual_smoke.find((row) => row.year === 2023).counties_exposed_at_least_once, 1646);
  assert.equal(data.extremes.top_days[0].date, "2023-06-29");
  assert.equal(data.extremes.days_exceeding_benchmark_since_2016, 36);
  assert.equal(data.regional_shift.top5_2023.share_percent, 52);
  assert.equal(data.fire_smoke_decoupling.canada_multiple_of_average, 6.1);
  assert.equal(data.meta.operational_proxy_start_year, 2024);
  assert.equal(data.meta.operational_proxy_end_year, 2026);
  assert.equal(data.meta.publication_cutoff_date, "2026-07-18");
  assert.equal(data.meta.operational_proxy_as_of_date, "2026-07-18");
  assert.deepEqual(data.operational_proxy.map((row) => row.year), [2024, 2025, 2026]);
  assert.deepEqual(data.operational_proxy.map((row) => row.broad_proxy_days), [6, 9, 4]);
  assert.deepEqual(data.operational_same_cutoff.map((row) => row.broad_proxy_days), [4, 4, 4]);
  assert.equal(data.operational_proxy.at(-1).status, "year_to_date_composite_snapshot");
  assert.equal(data.operational_proxy.at(-1).as_of_date, "2026-07-18");
  assert.equal(data.operational_proxy.at(-1).indicative_population_days, 214_762_361);
  assert.equal(data.operational_proxy.at(-1).peak_indicative_population, 58_881_904);
  assert.deepEqual(data.current_fire_activity.map((row) => row.burned_area_acres), [3_853_513, 7_202_012]);
  assert.ok(data.operational_proxy.every((row) => row.year > data.meta.smoke_series_end_year));
  assert.ok(data.sources.some((source) => source.id === "epa-aqs-daily"));
  assert.ok(data.sources.some((source) => source.id === "noaa-hms-smoke"));
  assert.ok(data.sources.some((source) => source.id === "epa-airnow-daily-pm25-2026-supplement"));
  assert.ok(data.sources.some((source) => source.id === "nifc-imsr-2026-07-18"));
  assert.ok(data.annual_smoke.every((row) => Number.isInteger(row.year)));
});

test("ships every linked downloadable dataset", async () => {
  const files = [
    "dashboard.json",
    "current_fire_activity_2026.csv",
    "large_fire_incidents_source_covered.csv",
    "large_fire_incidents_annual_source_covered.csv",
    "all_fire_incidents_annual_source_covered.csv",
    "all_fire_density_tiles_1992_2020.csv",
    "fire_year_context.csv",
    "smoke_region_context_2006_2023.csv",
    "documented_smoke_episodes_1950_2005.csv",
    "mtbs_wildfires_annual.csv",
    "canada_fire_annual.csv",
    "stanford_annual_smoke_2006_2023.csv",
    "stanford_daily_smoke_2006_2023.csv",
    "operational_smoke_proxy_annual_2024_2026.csv",
    "zcta_smoke_exposure_2021.csv",
    "source_manifest.json",
  ];

  for (const file of files) {
    const contents = await readFile(new URL(`../public/data/${file}`, import.meta.url), "utf8");
    assert.ok(contents.length > 20, `${file} should not be empty`);
  }
});

test("ships the report graphic as an Open Graph image", async () => {
  const image = await readFile(new URL("../public/og.png", import.meta.url));
  assert.ok(image.byteLength > 100_000);
  assert.equal(image.subarray(1, 4).toString("ascii"), "PNG");
});
