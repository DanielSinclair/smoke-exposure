"use client";

import { useEffect, useId, useRef, useState, type CSSProperties, type FocusEvent, type PointerEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";

export type AnnualSmoke = {
  year: number;
  broad_smoke_days: number;
  population_days: number;
  peak_population_exposed: number;
  peak_date: string;
  residents_exposed_at_least_once: number;
  share_exposed_at_least_once: number;
  per_capita_smoke_days: number;
  counties_exposed_at_least_once: number;
  severe_days_10m: number;
  burden_rank: number;
  record_year: boolean;
};

export type SmokeTrend = {
  early_period: string;
  recent_period: string;
  early_average_population_days: number;
  recent_average_population_days: number;
  recent_to_early_multiplier: number;
  early_per_capita_days: number;
  recent_per_capita_days: number;
  fixed_population: number;
  cumulative_population_days: number;
  cumulative_share_since_2019: number;
  cumulative_share_since_2017: number;
  rolling_mean_5yr: { year: number; value: number }[];
};

export type SmokeHistoryMonth = {
  status:
    | "no_comparable_daily_data"
    | "documented_event"
    | "modeled_comparable"
    | "operational_proxy"
    | "not_yet_observed";
  review_status?: "not_reviewed" | "searched_no_qualifying_case_found" | "reviewed_with_evidence" | string;
  evidence_level?: number | string | null;
  evidence_label?: string | null;
  observed_days: number | null;
  smoke_days: number | null;
  broad_days: number | null;
  population_days: number | null;
  peak_population_exposed: number | null;
  events: {
    event: string;
    event_name?: string;
    start_date?: string;
    end_date?: string;
    affected_regions: string;
    impacted_us_regions?: string;
    impacted_us_states?: string[] | string;
    source_fires: string;
    source_fire_names?: string[] | string;
    source_title: string;
    source_url: string;
    evidence_level?: number | string | null;
    evidence_label?: string | null;
    attribution_confidence?: string | null;
    pm25_metric?: string | number | null;
    aqi_metric?: string | number | null;
  }[];
};

export type FireHistoryGeography = {
  record_count: number | null;
  burned_acres: number | null;
  named_record_count: number | null;
  records_with_coordinates: number | null;
  certified_or_final_count: number | null;
  source_id: string | null;
  source_scope: string | null;
  coverage_tier: string;
  coverage_status: string;
  calendar_window_complete: boolean;
  provisional: boolean;
};

export type FireHistoryYear = {
  year: number;
  months: { united_states: FireHistoryGeography; canada: FireHistoryGeography }[];
};

export type FireIncidentCatalogYear = {
  year: number;
  geography: "United States" | "Canada";
  record_count: number | null;
  burned_acres: number | null;
  records_with_unknown_month: number | null;
  source_id: string | null;
  source_scope: string | null;
  coverage_tier: string;
  coverage_status: string;
  provisional: boolean;
};

export type Extremes = {
  top_days: { rank: number; date: string; population_exposed: number; share_of_population: number }[];
  benchmark_day: { date: string; population_exposed: number; label: string };
  days_exceeding_benchmark_since_2016: number;
  days_exceeding_benchmark_by_year: Record<string, number>;
  longest_streaks: { start_date: string; days: number }[];
  record_years: number[];
};

export type Seasonality = {
  era_1: { period: string; monthly_share: number[] };
  era_2: { period: string; monthly_share: number[] };
  notable_years: { year: number; month: number; share_percent: number }[];
};

export type RegionalShift = {
  top_state_by_year: { year: number; state: string; state_fips: string }[];
  top5_2023: { states: string[]; share_percent: number };
};

export type FireSmokeDecoupling = {
  year: number;
  us_mtbs_acres: number;
  us_mtbs_2013_2022_average_acres: number;
  us_change_vs_average_percent: number;
  canada_nbac_acres: number;
  canada_nbac_2013_2022_average_acres: number;
  canada_multiple_of_average: number;
  us_smoke_population_days: number;
  us_smoke_rank: number;
};

export type SmokeHistoryYear = { year: number; months: SmokeHistoryMonth[] };

export type OperationalProxy = {
  year: number;
  status: "calendar_year_snapshot_revisionable" | "year_to_date_snapshot" | "year_to_date_composite_snapshot";
  as_of_date: string;
  broad_proxy_days: number;
  indicative_population_days: number;
  peak_indicative_population: number;
  peak_date?: string;
};

export type OperationalCutoff = {
  year: number;
  cutoff: string;
  days_in_window: number;
  broad_proxy_days: number;
  indicative_population_days: number;
  peak_indicative_population: number;
  peak_date: string;
};

export type AnnualFire = {
  year: number;
  fire_count: number | null;
  acres_burned: number;
  provisional?: boolean;
};

export type FireTrend = {
  first_period: string;
  recent_period: string;
  first_average_acres: number;
  recent_average_acres: number;
  percent_change: number;
};

export type CurrentFireActivity = {
  year: number;
  geography: "United States" | "Canada";
  fire_count: number;
  burned_area_hectares: number | null;
  burned_area_acres: number;
  as_of_date: string;
  status: string;
  complete: boolean;
  comparable_to_historical_complete_series: boolean;
  source_dataset: string;
  source_url: string;
};

export type FireYearContext = {
  year: number;
  geography: "United States" | "Canada";
  rank: number;
  fire_name: string;
  label_kind: "reported_name" | "agency_incident_id";
  region: string;
  acres: number;
  source_dataset: string;
  provisional: boolean;
  causal_smoke_attribution: boolean;
};

export type SmokeRegionContext = {
  year: number;
  rank: number;
  state_fips: string;
  state: string;
  high_smoke_population_days: number;
  high_smoke_days: number;
  peak_population_exposed: number;
  model_id: string;
};

export type FireDensityTile = {
  x: number;
  y: number;
  year_start: number;
  year_end: number;
  fire_count: number;
  burned_acres: number;
  geographies: string[];
  label: string;
  source_ids: string[];
  us_fire_count?: number;
  canada_fire_count?: number;
  coverage_note?: string;
  level?: number;
};

export type FireDensityScale = {
  method: "distribution_quantiles";
  metric: "reported_burned_acres_per_grid_cell";
  probabilities: number[];
  thresholds: number[];
  top_decile_cell_count: number;
  top_decile_share_percent: number;
};

export type SmokeSameCutoff = {
  year: number;
  cutoff: string;
  series_kind: "stanford_modeled" | "operational_proxy";
  series_label: string;
  comparable_to_2026: boolean;
  days_in_window: number;
  broad_days: number;
  population_days: number;
  peak_population: number;
  peak_date: string;
  monitor_source_tier?: string;
  balanced_panel_population_days?: number;
  balanced_panel_broad_days?: number;
  balanced_panel_sites?: number;
};

export type SourceRecord = {
  id: string;
  title: string;
  organization: string;
  url: string;
  retrieval_url?: string | null;
  coverage: string;
  role: string;
  license?: string | null;
  grain?: string | null;
  comparable: boolean;
};

export type ResearchPaper = {
  id: string;
  title: string;
  citation: string;
  url: string;
  download_url?: string;
  status: string;
  role: string;
};

export type DashboardData = {
  meta: {
    generated_at: string;
    publication_cutoff_date: string;
    smoke_series_start_year: number;
    smoke_series_end_year: number;
    operational_proxy_as_of_date: string;
    same_cutoff_month_day: string;
    fire_density_geometry_version: string;
    fire_density_period: string;
  };
  annual_smoke: AnnualSmoke[];
  smoke_trend: SmokeTrend;
  extremes: Extremes;
  seasonality: Seasonality;
  regional_shift: RegionalShift;
  fire_smoke_decoupling: FireSmokeDecoupling;
  smoke_history: SmokeHistoryYear[];
  fire_history: FireHistoryYear[];
  fire_incident_catalog: FireIncidentCatalogYear[];
  operational_proxy: OperationalProxy[];
  operational_same_cutoff: OperationalCutoff[];
  smoke_same_cutoff: SmokeSameCutoff[];
  current_fire_activity: CurrentFireActivity[];
  fire_year_context: FireYearContext[];
  smoke_region_context: SmokeRegionContext[];
  fire_density_scale?: FireDensityScale;
  fire_density_tiles?: FireDensityTile[];
  annual_fire: AnnualFire[];
  annual_canada_fire?: AnnualFire[];
  fire_trends: { canada: FireTrend; united_states: FireTrend };
  sources: SourceRecord[];
  research_papers: ResearchPaper[];
};

const GITHUB_URL = "https://github.com/DanielSinclair/smoke-exposure";
const GITHUB_RAW_DATA_URL = "https://raw.githubusercontent.com/DanielSinclair/smoke-exposure/main/data/processed";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const publicPath = (path: string) => `${BASE_PATH}${path}`;
const X_URL = "https://x.com/_DanielSinclair";
const WASHINGTON_POST_URL = "https://www.washingtonpost.com/weather/2026/07/18/thick-wildfire-smoke-lingers-over-mid-atlantic-early-saturday/";
const BEN_NOLL_URL = "https://x.com/BenNollWeather/status/2078451048486961519";
const BEN_NOLL_GRAPHIC_URL = "https://pbs.twimg.com/media/HNgSoVqbEAAgqDD?format=png&name=large";

const DATASETS = [
  ["Stanford annual smoke, 2006–2023", publicPath("/data/stanford_annual_smoke_2006_2023.csv"), "Annual comparable exposure metrics used in the headline trend."],
  ["Stanford daily smoke, 2006–2023", publicPath("/data/stanford_daily_smoke_2006_2023.csv"), "County-day aggregation behind widespread days and person-days."],
  ["Monitor + satellite smoke check, 2024–2026", publicPath("/data/operational_smoke_proxy_annual_2024_2026.csv"), "Recent high-PM₂.₅ observations where NOAA also mapped smoke overhead."],
  ["Monitor + satellite annual screen, 2006–2026", publicPath("/data/operational_smoke_screen_annual_2006_2026.csv"), "A conceptually consistent annual AQS/HMS screen; 2026 adds preliminary AirNow and remains non-comparable with Stanford."],
  ["Monitor + satellite daily screen, 2006–2026", publicPath("/data/operational_smoke_screen_daily_2006_2026.csv"), "All 7,504 daily screen rows behind the annual and same-window summaries."],
  ["Monitor + satellite same-window screen", publicPath("/data/operational_smoke_screen_same_cutoff_2006_2026.csv"), "Every year compared from Jan 1 through July 18, with a fixed-site coverage sensitivity."],
  ["Monitor-network coverage audit", publicPath("/data/operational_smoke_screen_monitor_coverage_2006_2026.csv"), "Monitor counts, population footprint, HMS coverage, and balanced-panel size by year."],
  ["Monitor + satellite processing audit", publicPath("/data/operational_smoke_screen_audit_2006_2026.json"), "Threshold, event-row policy, source cutoffs, balanced-panel membership, and comparability boundary."],
  ["Canada annual burned area, 1972–2025", publicPath("/data/canada_fire_annual.csv"), "NBAC adjusted complete-year series."],
  ["U.S. mapped large-fire area, 1984–2024", publicPath("/data/mtbs_wildfires_annual.csv"), "MTBS complete historical extract."],
  ["Current fire activity, 2026", publicPath("/data/current_fire_activity_2026.csv"), "Preliminary NIFC and NRCan CWFIF year-to-date totals."],
  ["Historical large-fire incidents", publicPath("/data/large_fire_incidents_source_covered.csv"), "Every normalized source-covered U.S. and Canadian large-fire record; coverage varies by product, agency and year."],
  ["Historical large-fire annual rollup", publicPath("/data/large_fire_incidents_annual_source_covered.csv"), "Year-country counts and acres reconciled to the normalized incident table."],
  ["All-fire annual source rollup", publicPath("/data/all_fire_incidents_annual_source_covered.csv"), "Country-specific annual coverage from U.S. FPA FOD and the full Canadian NFDB point archive."],
  ["Monthly source-covered fire records, 1950–2026", publicPath("/data/fire_incidents_monthly_source_covered.csv"), "Month-country counts and recorded acres from one designated archive per era; blanks mean no national catalog."],
  ["Annual incident catalog, 1950–2026", publicPath("/data/fire_incidents_annual_catalog_1950_2026.csv"), "Annual reconciliation of the monthly source-covered incident catalog."],
  ["Incident catalog source lanes", publicPath("/data/fire_incident_catalog_sources.csv"), "Exact archive, scope and coverage boundary used for every country-year."],
  ["North American fire-density grid", publicPath("/data/all_fire_density_tiles_1992_2020.csv"), "The exact 30×24 spatial aggregate rendered in the reported-fire density map."],
  ["Annual fire context", publicPath("/data/fire_year_context.csv"), "Largest named or identified large-fire records by year and country for chart context."],
  ["Modeled smoke burden by state", publicPath("/data/smoke_region_context_2006_2023.csv"), "State-year exposure metrics reconstructed from the Stanford county estimates."],
  ["Historical smoke events, 1950–2005", publicPath("/data/historical_smoke_events_1950_2005.csv"), "One reviewed U.S. smoke-impact episode with evidence strength, attribution, regions, and source keys."],
  ["Historical smoke observations", publicPath("/data/historical_smoke_observations_1950_2005.csv"), "One source-specific observation supporting each interpreted event."],
  ["Historical smoke source index", publicPath("/data/historical_smoke_sources.csv"), "The original government and published sources behind the documentary record."],
  ["Historical monthly search ledger", publicPath("/data/historical_smoke_search_coverage_1950_2005.csv"), "Every month from 1950–2005 labeled documented, source-screened without a case, or not systematically reviewed."],
  ["NOAA wildfire candidate index", publicPath("/data/noaa_storm_events_wildfire_candidates_1950_2005.csv"), "NOAA Storm Events Wildfire records from 1996–2005; candidate context, not a smoke census."],
  ["Source manifest", publicPath("/data/source_manifest.json"), "Retrieval dates, checksums, roles and comparability notes for the project inputs."],
] as const;

const CONTEXT_SOURCE_IDS = new Set([
  "usa-today-2026-wildfire-graphs",
  "great-smoke-pall-1950",
  "nasa-quebec-smoke-2002",
  "ben-noll-2026-07-18",
  "washington-post-2026-07-18",
  "robert-rohde-2026-07-18",
  "berkeley-earth-cigarette-equivalence",
  "iqair-world-air-quality-report-2025",
  "aqli-methodology",
]);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const AQI_SCALE = [
  { low: 0, high: 50, label: "Good", color: "#00e400" },
  { low: 51, high: 100, label: "Moderate", color: "#ffff00" },
  { low: 101, high: 150, label: "Unhealthy for sensitive groups", color: "#ff7e00" },
  { low: 151, high: 200, label: "Unhealthy", color: "#ff0000" },
  { low: 201, high: 300, label: "Very unhealthy", color: "#8f3f97" },
  { low: 301, high: 500, label: "Hazardous", color: "#7e0023" },
] as const;

const formatCompact = (value: number, digits = 1) => {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(digits)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(digits)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(digits)}K`;
  return value.toLocaleString("en-US");
};

const formatRank = (rank: number) => {
  const teen = rank % 100;
  if (teen >= 11 && teen <= 13) return `${rank}th`;
  return `${rank}${rank % 10 === 1 ? "st" : rank % 10 === 2 ? "nd" : rank % 10 === 3 ? "rd" : "th"}`;
};

const formatCutoff = (isoDate: string) => {
  const [year, month, day] = isoDate.split("-").map(Number);
  return `${MONTHS[month - 1]} ${day}, ${year}`;
};
const formatMonthDay = (isoDate: string) => {
  const [, month, day] = isoDate.split("-").map(Number);
  return `${MONTHS[month - 1]} ${day}`;
};

type FloatingPosition = { left: number; top: number; below: boolean; maxHeight: number };

function positionFor(target: Element, panelWidth = 280): FloatingPosition {
  const box = target.getBoundingClientRect();
  const gutter = 12;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const availableWidth = Math.min(panelWidth, viewportWidth - gutter * 2);
  const idealLeft = box.left + box.width / 2 - availableWidth / 2;
  const left = Math.max(gutter, Math.min(idealLeft, viewportWidth - availableWidth - gutter));
  const availableAbove = Math.max(120, box.top - gutter - 9);
  const availableBelow = Math.max(120, viewportHeight - box.bottom - gutter - 9);
  const below = availableBelow >= availableAbove;
  return { left, top: below ? box.bottom + 9 : box.top - 9, below, maxHeight: below ? availableBelow : availableAbove };
}

function useDelayedTooltipClose(close: () => void) {
  const timer = useRef<number | null>(null);
  const closeRef = useRef(close);
  useEffect(() => { closeRef.current = close; }, [close]);
  const cancelClose = () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = null;
  };
  const scheduleClose = () => {
    cancelClose();
    timer.current = window.setTimeout(() => closeRef.current(), 140);
  };
  useEffect(() => cancelClose, []);
  return { cancelClose, scheduleClose };
}

function FloatingPanel({ id, position, className = "", children, onPointerEnter, onPointerLeave }: { id: string; position: FloatingPosition; className?: string; children: ReactNode; onPointerEnter?: () => void; onPointerLeave?: () => void }) {
  if (typeof document === "undefined") return null;
  return createPortal(
    <span
      id={id}
      className={`floating-panel ${position.below ? "below" : "above"} ${className}`}
      style={{ left: position.left, top: position.top, maxHeight: position.maxHeight }}
      role="tooltip"
      onPointerEnter={onPointerEnter}
      onPointerOver={onPointerEnter}
      onMouseOver={onPointerEnter}
      onPointerLeave={onPointerLeave}
    >
      {children}
    </span>,
    document.body,
  );
}

function HoverDetail({
  trigger,
  children,
  className = "",
  panelClassName = "",
  ariaLabel = "More information",
  style,
}: {
  trigger: ReactNode;
  children: ReactNode;
  className?: string;
  panelClassName?: string;
  ariaLabel?: string;
  style?: CSSProperties;
}) {
  const id = useId();
  const [position, setPosition] = useState<FloatingPosition | null>(null);
  const { cancelClose, scheduleClose } = useDelayedTooltipClose(() => setPosition(null));
  const panelWidth = panelClassName.includes("graphic-preview-panel") ? 430 : panelClassName.includes("aqi-panel") ? 360 : 280;
  const openFrom = (target: Element) => setPosition(positionFor(target, panelWidth));
  const openPointer = (event: PointerEvent<HTMLSpanElement>) => { cancelClose(); openFrom(event.currentTarget); };
  const openFocus = (event: FocusEvent<HTMLSpanElement>) => { cancelClose(); openFrom(event.currentTarget); };

  return (
    <span
      className={`hover-detail ${className}`}
      style={style}
      tabIndex={0}
      aria-label={ariaLabel}
      aria-describedby={position ? id : undefined}
      onPointerEnter={openPointer}
      onPointerOver={openPointer}
      onMouseOver={(event) => { cancelClose(); openFrom(event.currentTarget); }}
      onPointerLeave={(event) => { if (!event.currentTarget.matches(":focus")) scheduleClose(); }}
      onFocus={openFocus}
      onBlur={scheduleClose}
      onClick={(event) => { cancelClose(); openFrom(event.currentTarget); }}
      onKeyDown={(event) => { if (event.key === "Escape") setPosition(null); }}
    >
      {trigger}
      {position ? <FloatingPanel id={id} position={position} className={panelClassName} onPointerEnter={cancelClose} onPointerLeave={scheduleClose}>{children}</FloatingPanel> : null}
    </span>
  );
}

function BenNollGraphicLink({ children }: { children: ReactNode }) {
  return (
    <HoverDetail
      className="graphic-preview-trigger"
      panelClassName="graphic-preview-panel"
      ariaLabel="Ben Noll and Washington Post graphic. Hover or focus to preview; activate the link to open the source."
      trigger={<a href={BEN_NOLL_URL} target="_blank" rel="noreferrer">{children}</a>}
    >
      {/* The source image remains hosted by X; this site does not republish a local copy. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={BEN_NOLL_GRAPHIC_URL} alt="Scatter plot relating Canadian fire-season temperature and annual acres burned, 1972 to 2025" />
      <small>Ben Noll / The Washington Post · source: CNFDB and ERA5. Context only; preview loaded from the X-hosted original.</small>
    </HoverDetail>
  );
}

function PrintButton() {
  return (
    <button className="print-control" type="button" onClick={() => window.print()}>
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4.25 5V1.75h7.5V5M4.25 11H2.5V5.5h11V11h-1.75M4.25 8.75h7.5v5.5h-7.5z" /><circle cx="11.3" cy="7.25" r=".65" /></svg>
      Print / save PDF
    </button>
  );
}

function aqiCategory(value: number) {
  return AQI_SCALE.find((category) => value >= category.low && value <= category.high) ?? AQI_SCALE.at(-1)!;
}

function AqiBadge({ value, label, treatment }: { value: number; label?: string; treatment?: "plain" | "threshold" | "numeric" }) {
  const category = aqiCategory(value);
  const visibleLabel = label ?? `AQI ${value}`;
  const resolvedTreatment = treatment ?? (/\d/.test(visibleLabel) ? "numeric" : "plain");
  const textColor = value >= 151 ? "#ffffff" : "#111111";
  return (
    <HoverDetail
      className="aqi-hover"
      panelClassName="aqi-panel"
      ariaLabel={`${visibleLabel}: ${category.label}. Open for context.`}
      trigger={<span className={`aqi-badge ${resolvedTreatment}`} style={{ "--aqi-color": category.color, "--aqi-text": textColor } as CSSProperties}>{visibleLabel}</span>}
    >
      <strong className="aqi-panel-title"><span style={{ background: category.color }} />{`AQI ${value}: ${category.label}`}</strong>
      <span className="aqi-scale" aria-label="EPA AQI categories">
        {AQI_SCALE.map((item) => (
          <i className={value >= item.low && value <= item.high ? "active" : ""} key={item.low} style={{ background: item.color }}>
            <b>{item.low}{item.high === 500 ? "+" : `–${item.high}`}</b>
          </i>
        ))}
      </span>
      <span className="aqi-context-row"><b>Daily threshold</b><span>35.5 µg/m³ PM₂.₅ is where index 101 begins.</span></span>
      <span className="aqi-context-row"><b>Smoking analogy</b><span>At 35.5 µg/m³, Berkeley Earth’s rough rule is about 1.6 cigarette-equivalents for that day.</span></span>
      <span className="aqi-context-row"><b>Polluted-city scale</b><span>Loni, India averaged 112.5 µg/m³ across 2025; that annual average is not the same as one smoke day.</span></span>
      <span className="aqi-context-row"><b>Life expectancy</b><span>AQLI estimates 0.98 years lost per sustained additional 10 µg/m³—not from a single episode.</span></span>
      <small>Context sources: EPA, Berkeley Earth, IQAir 2025 and AQLI. Comparisons use different exposure periods.</small>
    </HoverDetail>
  );
}

function LeadMetric({ value, label, explanation, tooltip }: { value: string; label: string; explanation: string; tooltip: string }) {
  return (
    <article className="lead-metric">
      <HoverDetail
        className="metric-hover lead-metric-hover"
        ariaLabel={`${label}. Hover or focus for details.`}
        trigger={<span className="lead-metric-trigger"><strong>{value}</strong><b>{label}</b><span>{explanation}</span></span>}
      >
        {tooltip}
      </HoverDetail>
    </article>
  );
}

type TooltipRow = { label: string; value: ReactNode };
type LinePoint = { year: number; value: number; metricLabel: string; rows?: TooltipRow[]; open?: boolean };
type LineSeries = {
  key: string;
  label: string;
  color: string;
  points: LinePoint[];
  dash?: string;
  openPoints?: boolean;
  showPoints?: boolean;
  markerMode?: "filled" | "open" | "hover";
  markerRadius?: number;
  lineWidth?: number;
  lineOpacity?: number;
  legendRows?: TooltipRow[];
};
type SupplementalPoint = LinePoint & { seriesKey: string; label: string; color: string };
type ActiveChartPoint = { position: FloatingPosition; year: number; value: number; metricLabel: string; label: string; rows?: TooltipRow[]; color: string };

function tooltipAria(year: number, label: string, metricLabel: string, value: number, rows: TooltipRow[] = []) {
  const rowText = rows.map((row) => `${row.label}: ${typeof row.value === "string" || typeof row.value === "number" ? row.value : "details shown on screen"}`).join(". ");
  return `${year}. ${label}. ${metricLabel}: ${value.toLocaleString("en-US")}. ${rowText}`;
}

function TooltipRows({ rows }: { rows: TooltipRow[] }) {
  return (
    <dl className="tooltip-rows">
      {rows.map((row, index) => <div key={`${row.label}-${index}`}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}
    </dl>
  );
}

function InteractiveLineChart({
  series,
  maximum,
  tickYears,
  ariaLabel,
  perCapitaDenominator,
  supplementalPoints = [],
  height = 176,
}: {
  series: LineSeries[];
  maximum: number;
  tickYears: number[];
  ariaLabel: string;
  perCapitaDenominator?: number;
  supplementalPoints?: SupplementalPoint[];
  height?: number;
}) {
  const [active, setActive] = useState<ActiveChartPoint | null>(null);
  const tooltipId = useId();
  const { cancelClose, scheduleClose } = useDelayedTooltipClose(() => setActive(null));
  const width = 680;
  const left = 48;
  const right = perCapitaDenominator ? 50 : 12;
  const top = 13;
  const bottom = 27;
  const allPoints = [...series.flatMap((item) => item.points), ...supplementalPoints];
  const firstYear = Math.min(...allPoints.map((point) => point.year));
  const lastYear = Math.max(...allPoints.map((point) => point.year));
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const xForYear = (year: number) => left + ((year - firstYear) / (lastYear - firstYear)) * plotWidth;
  const yFor = (value: number) => top + plotHeight - (value / maximum) * plotHeight;
  const pathFor = (points: LinePoint[]) => points.map((point, index) => `${index === 0 ? "M" : "L"}${xForYear(point.year).toFixed(2)},${yFor(point.value).toFixed(2)}`).join(" ");
  const legendRows = (item: LineSeries): TooltipRow[] => {
    const values = item.points.map((point) => point.value);
    return [
      { label: "Coverage", value: `${item.points[0].year}–${item.points.at(-1)!.year} · ${item.points.length} annual points` },
      { label: "Observed range", value: `${formatCompact(Math.min(...values))}–${formatCompact(Math.max(...values))}` },
      ...(item.legendRows ?? []),
    ];
  };
  const gridValues = perCapitaDenominator
    ? [perCapitaDenominator * 1.5, perCapitaDenominator, perCapitaDenominator * .5, 0]
    : [maximum, maximum / 2, 0];
  const activate = (point: LinePoint, label: string, color: string, target: Element) => {
    cancelClose();
    setActive({
      position: positionFor(target, 270),
      year: point.year,
      value: point.value,
      metricLabel: point.metricLabel,
      label,
      rows: point.rows,
      color,
    });
  };

  return (
    <div className="chart-shell" onPointerLeave={(event) => { if (!event.currentTarget.contains(document.activeElement)) scheduleClose(); }}>
      {series.length ? (
        <div className="chart-legend">
          {series.map((item) => (
            <HoverDetail
              className="chart-legend-detail"
              key={item.key}
              ariaLabel={`${item.label}. Hover or focus for series details.`}
              trigger={<span><i className={`series-legend-line ${item.dash ? "dashed" : ""}`} style={{ borderTopColor: item.color, borderTopWidth: `${Math.max(item.lineWidth ?? 1.7, 1.5)}px` }} />{item.label}</span>}
            >
              <TooltipRows rows={legendRows(item)} />
            </HoverDetail>
          ))}
          {supplementalPoints.length ? (
            <HoverDetail
              className="chart-legend-detail"
              ariaLabel="2026 year-to-date markers. Hover or focus for details."
              trigger={<span><i className="current-marker-key" />2026 YTD</span>}
            >
              <TooltipRows rows={[
                { label: "Status", value: "Preliminary year-to-date markers; not connected to complete-year lines" },
                { label: "Markers", value: supplementalPoints.map((point) => `${point.label}: ${formatCompact(point.value)}`).join(" · ") },
              ]} />
            </HoverDetail>
          ) : null}
        </div>
      ) : null}
      <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        {gridValues.map((value) => {
          const y = yFor(value);
          return (
            <g key={value}>
              <line className="chart-grid" x1={left} x2={width - right} y1={y} y2={y} stroke="#e6e6e6" />
              <text className="axis-label" x={left - 7} y={y + 3} textAnchor="end" fill="#666666">{formatCompact(value, 0)}</text>
              {perCapitaDenominator && value ? <text className="axis-label per-capita-axis" x={width - right + 7} y={y + 3} textAnchor="start" fill="#666666">{(value / perCapitaDenominator).toFixed(1)} days/person</text> : null}
            </g>
          );
        })}
        {series.map((item) => <path className="data-line" d={pathFor(item.points)} fill="none" key={item.key} opacity={item.lineOpacity} stroke={item.color} strokeDasharray={item.dash} strokeWidth={item.lineWidth} />)}
        {series.flatMap((item) => item.showPoints === false ? [] : item.points.map((point) => {
          const x = xForYear(point.year);
          const y = yFor(point.value);
          return (
            <g
              className="chart-point-hit"
              key={`${item.key}-${point.year}`}
              tabIndex={0}
              focusable="true"
              role="button"
              aria-describedby={active?.year === point.year && active.label === item.label ? tooltipId : undefined}
              aria-label={tooltipAria(point.year, item.label, point.metricLabel, point.value, point.rows)}
              onPointerEnter={(event) => activate(point, item.label, item.color, event.currentTarget)}
              onPointerOver={(event) => activate(point, item.label, item.color, event.currentTarget)}
              onMouseOver={(event) => activate(point, item.label, item.color, event.currentTarget)}
              onClick={(event) => activate(point, item.label, item.color, event.currentTarget)}
              onFocus={(event) => activate(point, item.label, item.color, event.currentTarget)}
              onBlur={scheduleClose}
            >
              <circle className="point-hit-area" cx={x} cy={y} r="12" fill="transparent" stroke="none" />
              <circle
                className={`data-point marker-${item.markerMode ?? "default"}`}
                cx={x}
                cy={y}
                r={item.markerRadius ?? 2.6}
                fill={item.markerMode === "open" || (!item.markerMode && (point.open || item.openPoints)) ? "#ffffff" : item.color}
                stroke={item.color}
              />
            </g>
          );
        }))}
        {supplementalPoints.map((point) => {
          const x = xForYear(point.year);
          const y = yFor(point.value);
          return (
            <g
              className="chart-point-hit"
              key={`${point.seriesKey}-${point.year}-current`}
              tabIndex={0}
              focusable="true"
              role="button"
              aria-describedby={active?.year === point.year && active.label === `${point.label} · YTD` ? tooltipId : undefined}
              aria-label={tooltipAria(point.year, `${point.label} year to date`, point.metricLabel, point.value, point.rows)}
              onPointerEnter={(event) => activate(point, `${point.label} · YTD`, point.color, event.currentTarget)}
              onPointerOver={(event) => activate(point, `${point.label} · YTD`, point.color, event.currentTarget)}
              onMouseOver={(event) => activate(point, `${point.label} · YTD`, point.color, event.currentTarget)}
              onClick={(event) => activate(point, `${point.label} · YTD`, point.color, event.currentTarget)}
              onFocus={(event) => activate(point, `${point.label} · YTD`, point.color, event.currentTarget)}
              onBlur={scheduleClose}
            >
              <circle className="point-hit-area" cx={x} cy={y} r="14" fill="transparent" stroke="none" />
              <circle className="current-point-ring" cx={x} cy={y} r="6" fill="none" stroke={point.color} />
              <circle className="current-point" cx={x} cy={y} r="3.1" fill={point.color} stroke={point.color} />
            </g>
          );
        })}
        {tickYears.map((year) => <text className="axis-label" key={year} x={xForYear(year)} y={height - 5} textAnchor="middle" fill="#666666">{year}</text>)}
      </svg>
      {active ? (
        <FloatingPanel id={tooltipId} position={active.position} className="chart-point-floating-panel" onPointerEnter={cancelClose} onPointerLeave={scheduleClose}>
          <strong>{active.year} · {active.label}</strong>
          <TooltipRows rows={[{ label: active.metricLabel, value: active.value.toLocaleString("en-US") }, ...(active.rows ?? [])]} />
        </FloatingPanel>
      ) : null}
    </div>
  );
}

function SmokeTrendChart({ data, trend, extremes, fireContext, regionContext }: { data: AnnualSmoke[]; trend: SmokeTrend; extremes: Extremes; fireContext: FireYearContext[]; regionContext: SmokeRegionContext[] }) {
  const recordYears = new Set(extremes.record_years);
  const yearRows = (row: AnnualSmoke): TooltipRow[] => {
    const regions = regionContext
      .filter((item) => item.year === row.year && item.rank <= 3)
      .map((item) => `${item.state} ${formatCompact(item.high_smoke_population_days)}`)
      .join(", ");
    const fires = fireContext
      .filter((item) => item.year === row.year && !item.provisional)
      .sort((a, b) => b.acres - a.acres)
      .slice(0, 4)
      .map((item) => `${item.fire_name} (${item.region})`)
      .join(", ");
    return [
      { label: "Date", value: String(row.year) },
      { label: "Event context", value: fires || "No source-covered named fire record" },
      { label: "Affected regions", value: regions || "No state above the high-smoke threshold" },
      { label: "Source / status", value: "Stanford ECHO v2 beta · comparable modeled year" },
      { label: "Widespread days", value: `${row.broad_smoke_days.toLocaleString("en-US")} · 10M+ residents at once` },
      { label: "Days per person", value: row.per_capita_smoke_days.toFixed(2) },
      { label: "Reached at least once", value: `${formatCompact(row.residents_exposed_at_least_once)} · ${row.share_exposed_at_least_once.toFixed(1)}%` },
      { label: "Counties touched", value: `${row.counties_exposed_at_least_once.toLocaleString("en-US")} of 3,108` },
      { label: "Year rank", value: `${formatRank(row.burden_rank)} highest of ${data.length}` },
      { label: "Peak daily reach", value: formatCompact(row.peak_population_exposed) },
      ...(recordYears.has(row.year) ? [{ label: "Record", value: "New national cumulative-burden record at the time" }] : []),
      { label: "Attribution", value: "Fire names are annual context, not plume attribution" },
    ];
  };

  const annualPoints = data.map((row): LinePoint => ({
    year: row.year,
    value: row.population_days,
    metricLabel: "Person-days of unhealthy smoke air",
    rows: yearRows(row),
  }));
  const rollingPoints = trend.rolling_mean_5yr.map((row): LinePoint => ({
    year: row.year,
    value: row.value,
    metricLabel: "Trailing 5-year average",
  }));

  return (
    <figure className="trend-figure">
      <div className="figure-heading">
        <div><h3>Annual exposure and five-year trend</h3><p>Person-days of unhealthy smoke air · fixed 2020 population · 2006–2023</p></div>
        <div className="figure-number"><HoverDetail className="metric-hover" trigger={<span className="figure-number-trigger"><strong>{formatCompact(trend.cumulative_population_days, 2)}</strong><span>person-days since 2006</span></span>}>{trend.cumulative_share_since_2019}% occurred in 2019–2023; {trend.cumulative_share_since_2017}% occurred since 2017.</HoverDetail></div>
      </div>
      <InteractiveLineChart
        series={[
          { key: "smoke", label: "Annual estimate", color: "#8A8A84", lineWidth: 1.15, lineOpacity: .72, markerMode: "filled", markerRadius: 2.1, points: annualPoints, legendRows: [{ label: "Reading", value: "Thin gray line · individual annual estimates" }, { label: "Metric", value: "Sum of fixed residents above the smoke threshold on every qualifying county-day" }, { label: "Source", value: "Stanford ECHO v2 beta · comparable modeled series" }] },
          { key: "rolling", label: "5-year average trend", color: "#1B365D", lineWidth: 2.6, markerMode: "hover", points: rollingPoints, legendRows: [{ label: "Reading", value: "Blue line · trailing five-year trend; points appear only on hover or focus" }, { label: "Calculation", value: "Arithmetic mean of the current year and four preceding complete years" }, { label: "Purpose", value: "Shows the underlying burden trend while retaining annual volatility as context" }] },
        ]}
        maximum={600_000_000}
        tickYears={[2006, 2010, 2014, 2018, 2023]}
        ariaLabel="Annual modeled wildfire-smoke person-days from 2006 through 2023 with a trailing five-year average and a days-per-person scale"
        perCapitaDenominator={trend.fixed_population}
      />
      <figcaption><span className="line-key annual" /> thin gray: individual years <span className="line-key trend" /> blue: trailing five-year average. Hover either series for exact values and annual context. The right scale expresses the same burden as days per fixed resident.</figcaption>
    </figure>
  );
}

function WorstDays({ extremes, fireContext, regionContext }: { extremes: Extremes; fireContext: FireYearContext[]; regionContext: SmokeRegionContext[] }) {
  const [active, setActive] = useState<{ position: FloatingPosition; key: string; rows: TooltipRow[] } | null>(null);
  const id = useId();
  const { cancelClose, scheduleClose } = useDelayedTooltipClose(() => setActive(null));
  const maximumShare = Math.max(...extremes.top_days.map((row) => row.share_of_population));
  const show = (target: Element, key: string, rows: TooltipRow[]) => { cancelClose(); setActive({ position: positionFor(target, 320), key, rows }); };
  const rowDetails = (dateValue: string): TooltipRow[] => {
    const year = Number(dateValue.slice(0, 4));
    const fires = fireContext.filter((item) => item.year === year).sort((a, b) => b.acres - a.acres).slice(0, 4).map((item) => `${item.fire_name} (${item.region})`).join(", ");
    const regions = regionContext.filter((item) => item.year === year && item.rank <= 3).map((item) => `${item.state} ${formatCompact(item.high_smoke_population_days)}`).join(", ");
    return [
      { label: "Date", value: formatCutoff(dateValue) },
      { label: "Event context", value: fires || "No source-covered named fire record" },
      { label: "Affected regions", value: regions || "No state summary available" },
      { label: "Source / status", value: "Stanford ECHO v2 beta · comparable modeled day" },
      { label: "Attribution", value: "Fire names are same-year context, not plume attribution" },
    ];
  };
  const benchmarkYears = Object.entries(extremes.days_exceeding_benchmark_by_year).map(([year, days]) => `${year}: ${days}`).join(" · ");
  const streakSummary = extremes.longest_streaks.map((row) => `${formatCutoff(row.start_date)}: ${row.days} days`).join(" · ");

  return (
    <figure className="extremes-figure" onPointerLeave={scheduleClose} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) scheduleClose(); }}>
      <div className="figure-heading"><div><h3>The worst individual smoke days</h3><p>Largest modeled daily reach · comparable series, 2006–2023</p></div></div>
      <table className="extremes-table">
        <thead><tr><th>Rank</th><th>Date</th><th>People reached</th><th>Share of fixed population</th></tr></thead>
        <tbody>
          {extremes.top_days.map((row) => {
            const key = row.date;
            const shareText = row.share_of_population >= 25 ? `${row.share_of_population.toFixed(1)}% · more than 1 in 4` : row.share_of_population >= 20 ? `${row.share_of_population.toFixed(1)}% · more than 1 in 5` : `${row.share_of_population.toFixed(1)}%`;
            return (
              <tr key={key} tabIndex={0} aria-label={`${formatRank(row.rank)}. ${formatCutoff(row.date)}. ${row.population_exposed.toLocaleString("en-US")} residents, ${row.share_of_population.toFixed(1)} percent.`} aria-describedby={active?.key === key ? id : undefined} onPointerEnter={(event) => show(event.currentTarget, key, rowDetails(row.date))} onPointerOver={(event) => show(event.currentTarget, key, rowDetails(row.date))} onMouseOver={(event) => show(event.currentTarget, key, rowDetails(row.date))} onClick={(event) => show(event.currentTarget, key, rowDetails(row.date))} onFocus={(event) => show(event.currentTarget, key, rowDetails(row.date))}>
                <td>{row.rank}</td><td>{formatCutoff(row.date)}</td><td>{formatCompact(row.population_exposed)}</td>
                <td><span className="extreme-share-label">{shareText}</span><span className="extreme-bar"><i style={{ width: `${row.share_of_population / maximumShare * 100}%` }} /></span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {active ? <FloatingPanel id={id} position={active.position} onPointerEnter={cancelClose} onPointerLeave={scheduleClose}><TooltipRows rows={active.rows} /></FloatingPanel> : null}
      <figcaption><HoverDetail className="metric-hover" trigger={<span>The worst day of 2006–2010 reached {formatCompact(extremes.benchmark_day.population_exposed)} people. {extremes.days_exceeding_benchmark_since_2016} days since 2016 exceeded it; the longest continuous stretch lasted {extremes.longest_streaks[0].days} days in September 2020.</span>}>Benchmark: {formatCutoff(extremes.benchmark_day.date)}. Exceedances by year: {benchmarkYears}. Longest annual streaks: {streakSummary}.</HoverDetail></figcaption>
    </figure>
  );
}

const STATE_ABBREVIATIONS: Record<string, string> = {
  California: "CA", Florida: "FL", Georgia: "GA", Massachusetts: "MA", Nevada: "NV", "New York": "NY", Oregon: "OR", Washington: "WA",
};
function quantileThresholds(values: number[], bands = 5) {
  const sorted = values.filter((value) => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
  if (!sorted.length) return [];
  return Array.from({ length: bands - 1 }, (_, index) => {
    const position = (sorted.length - 1) * ((index + 1) / bands);
    const lower = Math.floor(position);
    const upper = Math.ceil(position);
    return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
  });
}

function quantileLevel(value: number, thresholds: number[]) {
  if (value <= 0) return 0;
  return Math.min(5, 1 + thresholds.filter((threshold) => value > threshold).length);
}

function SeasonalityAndRegions({ seasonality, regionalShift, regionContext }: { seasonality: Seasonality; regionalShift: RegionalShift; regionContext: SmokeRegionContext[] }) {
  const eras = [seasonality.era_1, seasonality.era_2];
  const maximumShare = Math.max(...eras.flatMap((era) => era.monthly_share));
  const june2023 = seasonality.notable_years.find((row) => row.year === 2023)!;
  const leadingBurdenByYear = new Map(regionContext.filter((row) => row.rank === 1).map((row) => [row.year, row]));
  const regionalThresholds = quantileThresholds([...leadingBurdenByYear.values()].map((row) => row.high_smoke_population_days));
  return (
    <figure className="seasonality-figure">
      <div className="figure-heading"><div><h3>When and where the burden concentrated</h3><p>Monthly share of person-days, then each year’s leading state shaded by burden</p></div></div>
      <div className="seasonality-strips">
        {eras.map((era) => <div className="seasonality-row" key={era.period}><strong>{era.period}</strong><div className="seasonality-cells">{era.monthly_share.map((share, monthIndex) => <HoverDetail key={`${era.period}-${monthIndex}`} className="seasonality-hover" ariaLabel={`${MONTHS[monthIndex]}, ${era.period}: ${share.toFixed(1)} percent of era person-days`} style={{ "--seasonality-opacity": Math.max(.04, share / maximumShare) } as CSSProperties} trigger={<span className="seasonality-cell"><i /><b>{MONTHS[monthIndex][0]}</b></span>}>{MONTHS[monthIndex]} accounted for {share.toFixed(1)}% of all modeled person-days in {era.period}.</HoverDetail>)}</div></div>)}
      </div>
      <div className="regional-shift-row">
        <strong>Top state</strong>
        <div className="regional-cells">
          {regionalShift.top_state_by_year.map((row) => {
            const leading = leadingBurdenByYear.get(row.year);
            const level = quantileLevel(leading?.high_smoke_population_days ?? 0, regionalThresholds);
            const leaders = regionContext.filter((item) => item.year === row.year && item.rank <= 3).map((item) => `${item.state} ${formatCompact(item.high_smoke_population_days)}`).join(", ");
            return <HoverDetail key={row.year} className={`regional-cell-hover level-${level}`} ariaLabel={`${row.year}: ${row.state} had the highest modeled burden, ${leading?.high_smoke_population_days.toLocaleString("en-US") ?? "not available"} population-days`} trigger={<span className="regional-cell"><b>{STATE_ABBREVIATIONS[row.state] ?? row.state.slice(0, 2).toUpperCase()}</b><i>{String(row.year).slice(2)}</i></span>}><TooltipRows rows={[{ label: "Year", value: String(row.year) }, { label: "Leading state", value: row.state }, { label: "State burden", value: leading ? `${leading.high_smoke_population_days.toLocaleString("en-US")} population-days` : "Not available" }, { label: "Top three", value: leaders }]} /></HoverDetail>;
          })}
        </div>
      </div>
      <div className="regional-scale"><span>Lower leading-state burden</span>{[1, 2, 3, 4, 5].map((level) => <i className={`level-${level}`} key={level} />)}<span>Higher</span></div>
      <figcaption><HoverDetail className="metric-hover" trigger={<span>June now carries the largest share of the recent-era burden; {june2023.share_percent.toFixed(0)}% of 2023’s person-days occurred in June. New York led in 2023, while five northeastern and midwestern states carried {regionalShift.top5_2023.share_percent}% of the national burden.</span>}>The seasonal strips sum daily modeled exposure by calendar month within each era. The 2023 top-five states were {regionalShift.top5_2023.states.join(", ")}.</HoverDetail></figcaption>
    </figure>
  );
}

function historyLevel(days: number) {
  if (days === 0) return 0;
  if (days <= 3) return 1;
  if (days <= 7) return 2;
  if (days <= 14) return 3;
  return 4;
}

type HistoricalEvidenceKind = "unreviewed" | "reviewed" | "documentary-1" | "documentary-2" | "documentary-3" | "quantified" | "modeled" | "operational" | "future";

function evidenceLevel(month: SmokeHistoryMonth) {
  const values = [month.evidence_level, ...month.events.map((event) => event.evidence_level)]
    .map((value) => typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10))
    .filter(Number.isFinite);
  return values.length ? Math.max(...values) : (month.events.length ? 1 : 0);
}

function historicalEvidenceKind(month: SmokeHistoryMonth): HistoricalEvidenceKind {
  if (month.status === "not_yet_observed") return "future";
  if (month.status === "modeled_comparable") return "modeled";
  if (month.status === "operational_proxy") return "operational";
  const level = evidenceLevel(month);
  const quantified = level >= 4 || month.events.some((event) => event.pm25_metric != null || event.aqi_metric != null);
  if (quantified) return "quantified";
  if (month.events.length) return `documentary-${Math.min(3, Math.max(1, level))}` as HistoricalEvidenceKind;
  if (month.review_status === "searched_no_qualifying_case_found") return "reviewed";
  return "unreviewed";
}

function eventValue(value: string[] | string | undefined, fallback: string) {
  if (Array.isArray(value)) return value.join(", ") || fallback;
  return value || fallback;
}

function historyTooltip(
  year: number,
  monthIndex: number,
  month: SmokeHistoryMonth,
  fireRecords: { united_states: FireHistoryGeography; canada: FireHistoryGeography },
  observationCutoff: string,
  fireContext: FireYearContext[],
  regionContext: SmokeRegionContext[],
) {
  const period = `${MONTHS[monthIndex]} ${year}`;
  const fireRows = ([
    ["U.S. fire records", fireRecords.united_states],
    ["Canadian fire records", fireRecords.canada],
  ] as const).flatMap(([label, fire]) => fire.record_count === null ? [{
    label,
    value: `No source-covered national catalog · ${fire.coverage_status.replaceAll("_", " ")}`,
  }] : [{
    label,
    value: `${fire.record_count.toLocaleString("en-US")} · ${formatCompact(fire.burned_acres ?? 0)} recorded acres${fire.provisional ? " · provisional" : ""}`,
  }, {
    label: `${label} source`,
    value: `${fire.source_scope} · reporting coverage varies`,
  }]);
  const kind = historicalEvidenceKind(month);
  const eventRows: TooltipRow[] = month.events.flatMap((event) => {
    const name = event.event_name || event.event;
    const date = event.start_date ? `${formatCutoff(event.start_date)}${event.end_date && event.end_date !== event.start_date ? `–${formatCutoff(event.end_date)}` : ""}` : period;
    const level = event.evidence_label || month.evidence_label || (event.evidence_level != null ? `Level ${event.evidence_level}` : month.evidence_level != null ? `Level ${month.evidence_level}` : "Documented case");
    return [
      { label: "Event", value: name },
      { label: "Dates", value: date },
      { label: "Origin fires", value: eventValue(event.source_fire_names, event.source_fires || "Not resolved") },
      { label: "Impacted U.S. regions", value: eventValue(event.impacted_us_regions || event.impacted_us_states, event.affected_regions || "Not resolved") },
      { label: "Evidence", value: `${level}${event.attribution_confidence ? ` · ${event.attribution_confidence} attribution` : ""}` },
      ...(event.pm25_metric != null ? [{ label: "PM₂.₅ evidence", value: String(event.pm25_metric) }] : []),
      ...(event.aqi_metric != null ? [{ label: "AQI evidence", value: String(event.aqi_metric) }] : []),
      ...(event.source_url ? [{ label: "Source", value: <a href={event.source_url} target="_blank" rel="noreferrer">{event.source_title || "Original source"} →</a> }] : []),
    ];
  });
  if (month.status === "no_comparable_daily_data") {
    const rows: TooltipRow[] = [
      { label: "Date", value: period },
      { label: "Evidence status", value: kind === "reviewed" ? "Reviewed; no qualifying case found" : month.events.length ? "Documented, not nationally comparable" : "Not yet systematically reviewed" },
      ...eventRows,
      ...fireRows,
      { label: "Interpretation", value: "Fire records do not establish that smoke affected U.S. air quality" },
    ];
    return { aria: `${period}. ${kind === "reviewed" ? "Reviewed; no qualifying documented case found." : month.events.length ? `${month.events.length} documented smoke ${month.events.length === 1 ? "episode" : "episodes"}.` : "Not systematically reviewed."} No comparable daily national wildfire-smoke estimate.`, rows };
  }
  if (month.status === "not_yet_observed") {
    const rows: TooltipRow[] = [
      { label: "Date", value: period },
      { label: "Event", value: "Not yet observed" },
      { label: "Affected regions", value: "Not available" },
      { label: "Source / status", value: `Outside the ${formatCutoff(observationCutoff)} cutoff` },
      { label: "Chart metrics", value: "Not available" },
      ...eventRows,
      ...fireRows,
    ];
    return { aria: `${period}. Outside the ${formatCutoff(observationCutoff)} observation cutoff.`, rows };
  }
  const source = month.status === "modeled_comparable" ? "Stanford ECHO model" : "preliminary AQS/AirNow + NOAA HMS estimate";
  const regions = regionContext.filter((item) => item.year === year && item.rank <= 3).map((item) => item.state).join(", ");
  const fireNames = fireContext
    .filter((item) => item.year === year)
    .sort((a, b) => b.acres - a.acres)
    .slice(0, 3)
    .map((item) => `${item.fire_name} (${item.region})`)
    .join(", ");
  const rows: TooltipRow[] = [
    { label: "Date", value: period },
    { label: "Event context", value: fireNames || "No source-covered named fire record" },
    { label: "Affected regions", value: regions || "Not available in this monthly aggregate" },
    { label: "Source / status", value: `${source} · ${month.status === "modeled_comparable" ? "comparable" : "preliminary, non-comparable"}` },
    { label: "Exposure days", value: (month.smoke_days ?? 0).toLocaleString("en-US") },
    { label: "Widespread days", value: (month.broad_days ?? 0).toLocaleString("en-US") },
    { label: "Worst single day", value: `${formatCompact(month.peak_population_exposed ?? 0)}${month.status === "operational_proxy" ? " indicative residents" : " residents"}` },
    { label: "Person-days", value: formatCompact(month.population_days ?? 0) },
    { label: "Daily records", value: (month.observed_days ?? 0).toLocaleString("en-US") },
    ...eventRows,
    ...fireRows,
    { label: "Interpretation", value: "Fire records are context unless a cited source explicitly links them to smoke" },
  ];
  return { aria: `${period}. ${month.smoke_days ?? 0} smoke-exposure days. ${month.broad_days ?? 0} widespread days. ${formatCompact(month.population_days ?? 0)} person-days. ${source}.`, rows };
}

function reviewCoverageLevel(reviewedMonths: number) {
  if (reviewedMonths === 0) return 0;
  if (reviewedMonths <= 3) return 1;
  if (reviewedMonths <= 8) return 2;
  if (reviewedMonths <= 11) return 3;
  return 4;
}

function SmokeHistory({ rows, fireRows, observationCutoff, fireContext, regionContext }: { rows: SmokeHistoryYear[]; fireRows: FireHistoryYear[]; observationCutoff: string; fireContext: FireYearContext[]; regionContext: SmokeRegionContext[] }) {
  const [active, setActive] = useState<{ position: FloatingPosition; key: string; rows: TooltipRow[] } | null>(null);
  const id = useId();
  const { cancelClose, scheduleClose } = useDelayedTooltipClose(() => setActive(null));
  const evidenceRows = rows.filter((row) => row.months.some((month) => month.events.length > 0 || month.status === "modeled_comparable" || month.status === "operational_proxy"));
  const historicalRows = rows.filter((row) => row.year <= 2005);
  const fireByYear = new Map(fireRows.map((row) => [row.year, row]));
  const documentaryCount = evidenceRows.filter((row) => row.year <= 2005).length;
  const modeledCount = evidenceRows.filter((row) => row.year >= 2006 && row.year <= 2023).length;
  const operationalCount = evidenceRows.filter((row) => row.year >= 2024).length;
  const show = (target: Element, key: string, tooltipRows: TooltipRow[]) => { cancelClose(); setActive({ position: positionFor(target, 320), key, rows: tooltipRows }); };
  const evidenceColumnStyle = { "--history-columns": evidenceRows.length } as CSSProperties;
  const coverageColumnStyle = { "--coverage-columns": historicalRows.length } as CSSProperties;
  const coverageTicks = [1950, 1960, 1970, 1980, 1990, 2000, 2005];

  return (
    <div className="history-figures">
      <figure
        className="history-figure evidence-history-figure"
        onPointerLeave={scheduleClose}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) scheduleClose();
        }}
      >
        <div className="figure-heading">
          <div><h3>U.S. wildfire-smoke evidence: years with available data</h3><p>Thirty non-contiguous years · one month per square · grayscale represents evidence or exposure intensity</p></div>
        </div>
        <div className="history-chart evidence-history-chart" style={evidenceColumnStyle}>
          <div className="history-era-row">
            <span />
            <div className="history-era-band">
              <b style={{ gridColumn: `1 / span ${documentaryCount}` }}>Documented reports</b>
              <b style={{ gridColumn: `${documentaryCount + 1} / span ${modeledCount}` }}>Modeled estimates</b>
              <b style={{ gridColumn: `${documentaryCount + modeledCount + 1} / span ${operationalCount}` }}>Recent screen</b>
            </div>
          </div>
          <div className="history-axis-row evidence-axis-row">
            <span />
            <div className="history-axis evidence-year-axis">
              {evidenceRows.map((row) => <span key={row.year}>{row.year}</span>)}
            </div>
          </div>
          {MONTHS.map((monthName, monthIndex) => (
            <div className="history-row" key={monthName}>
              <span className="month-label">{monthName}</span>
              <div className="history-months">
                {evidenceRows.map((row) => {
                  const month = row.months[monthIndex];
                  const monthlyFires = fireByYear.get(row.year)!.months[monthIndex];
                  const level = historyLevel(month.smoke_days ?? 0);
                  const evidenceKind = historicalEvidenceKind(month);
                  const displayedKind = evidenceKind === "quantified" ? "documentary-3" : month.events.length || ["modeled", "operational", "future"].includes(evidenceKind) ? evidenceKind : "none";
                  const detail = historyTooltip(row.year, monthIndex, month, monthlyFires, observationCutoff, fireContext, regionContext);
                  const detailKey = `${row.year}-${monthIndex}`;
                  const keyboardDetail = month.events.length > 0 || month.status !== "no_comparable_daily_data";
                  return (
                    <span
                      className={`history-cell level-${level} evidence-${displayedKind}`}
                      key={row.year}
                      tabIndex={keyboardDetail ? 0 : -1}
                      aria-label={detail.aria}
                      aria-describedby={active?.key === detailKey ? id : undefined}
                      onPointerEnter={(event) => show(event.currentTarget, detailKey, detail.rows)}
                      onPointerOver={(event) => show(event.currentTarget, detailKey, detail.rows)}
                      onMouseOver={(event) => show(event.currentTarget, detailKey, detail.rows)}
                      onClick={(event) => show(event.currentTarget, detailKey, detail.rows)}
                      onFocus={(event) => show(event.currentTarget, detailKey, detail.rows)}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        {active ? <FloatingPanel id={id} position={active.position} className="history-floating-panel" onPointerEnter={cancelClose} onPointerLeave={scheduleClose}><TooltipRows rows={active.rows} /></FloatingPanel> : null}
        <div className="history-legend evidence-legend">
          <HoverDetail className="legend-detail" trigger={<span className="legend-detail-trigger"><span>documented strength</span>{[1, 2, 3].map((level) => <i className={`history-cell evidence-documentary-${level}`} key={level} />)}<span>1 · 2 · 3+</span></span>}>Pre-2006 shades summarize documentary evidence strength. Exact events, regions, dates and sources remain available on hover.</HoverDetail>
          <HoverDetail className="legend-detail" ariaLabel="Comparable modeled smoke-day scale. Hover or focus for details." trigger={<span className="legend-detail-trigger"><span>modeled smoke days</span>{[0, 1, 2, 3, 4].map((level) => <i className={`history-cell evidence-modeled level-${level}`} key={level} />)}<span>0 · 1–3 · 4–7 · 8–14 · 15+</span></span>}>Grayscale intensity encodes qualifying modeled exposure days in 2006–2023, not PM₂.₅ concentration.</HoverDetail>
          <HoverDetail className="legend-detail" trigger={<span className="legend-detail-trigger"><i className="history-cell evidence-operational level-2" /><span>recent screen</span></span>}>Dashed 2024–2026 cells use monitor and satellite evidence. They are timely context and are not comparable with the Stanford wildfire-attribution model.</HoverDetail>
          <HoverDetail className="legend-detail" trigger={<span className="legend-detail-trigger"><i className="history-cell evidence-future" /><span>not yet observed</span></span>}>Months after {formatCutoff(observationCutoff)} contain no observation yet.</HoverDetail>
        </div>
        <figcaption>The columns intentionally skip years without accepted documentary evidence or national monthly estimates. This removes empty decades while keeping documentary reports, modeled estimates and the recent screen visibly separated.</figcaption>
      </figure>

      <figure className="review-coverage-figure">
        <div className="same-window-heading"><strong>Historical source-review coverage, 1950–2005</strong><span>one square per year · months systematically reviewed</span></div>
        <div className="review-coverage-chart" style={coverageColumnStyle}>
          <div className="review-coverage-axis">
            {coverageTicks.map((year) => <span key={year} style={{ gridColumn: year - historicalRows[0].year + 1 }}>{year}</span>)}
          </div>
          <div className="review-coverage-cells">
            {historicalRows.map((row) => {
              const isReviewed = (month: SmokeHistoryMonth) => month.review_status === "searched_no_qualifying_case_found" || month.review_status === "reviewed_with_evidence";
              const reviewedMonths = row.months.filter(isReviewed).length;
              const episodes = row.months.reduce((total, month) => total + month.events.length, 0);
              const reviewedMonthNames = row.months.flatMap((month, index) => isReviewed(month) ? [MONTHS[index]] : []);
              const level = reviewCoverageLevel(reviewedMonths);
              return (
                <HoverDetail
                  className="review-coverage-detail"
                  key={row.year}
                  ariaLabel={`${row.year}: ${reviewedMonths} of 12 months systematically reviewed`}
                  trigger={<span className={`review-coverage-cell level-${level}`} />}
                >
                  <TooltipRows rows={[{ label: "Year", value: String(row.year) }, { label: "Months reviewed", value: `${reviewedMonths} of 12${reviewedMonthNames.length ? ` · ${reviewedMonthNames.join(", ")}` : ""}` }, { label: "Accepted episodes", value: episodes.toLocaleString("en-US") }, { label: "Interpretation", value: episodes ? "Accepted episodes are documented cases; unreviewed months remain unknown" : reviewedMonths ? "Reviewed months with no accepted case are not proof that no smoke occurred" : "Not systematically reviewed; unknown, not zero" }]} />
                </HoverDetail>
              );
            })}
          </div>
        </div>
        <div className="coverage-legend"><span>months reviewed</span>{[[0, "0"], [1, "1–3"], [2, "4–8"], [3, "9–11"], [4, "12"]].map(([level, label]) => <span key={level}><i className={`review-coverage-cell level-${level}`} />{label}</span>)}</div>
        <figcaption>Systematic month-by-month source screening begins in 1996. Earlier accepted episodes mark documented cases, not complete annual review. Unreviewed years remain unknown rather than zero.</figcaption>
      </figure>
    </div>
  );
}

function fireRecordLevel(count: number | null, thresholds: number[]) {
  if (count === null) return -1;
  return quantileLevel(count, thresholds);
}

function AnnualFireRecordHistory({ catalog, smokeHistory, modeled, recent, fireContext }: { catalog: FireIncidentCatalogYear[]; smokeHistory: SmokeHistoryYear[]; modeled: AnnualSmoke[]; recent: OperationalProxy[]; fireContext: FireYearContext[] }) {
  const [active, setActive] = useState<{ position: FloatingPosition; key: string; rows: TooltipRow[] } | null>(null);
  const id = useId();
  const { cancelClose, scheduleClose } = useDelayedTooltipClose(() => setActive(null));
  const years = Array.from({ length: 77 }, (_, index) => 1950 + index);
  const geographies = ["United States", "Canada"] as const;
  const firstYear = years[0];
  const tickYears = [1950, 1970, 1990, 2006, 2020, 2026];
  const columnStyle = { "--history-columns": years.length } as CSSProperties;
  const byKey = new Map(catalog.map((row) => [`${row.geography}-${row.year}`, row]));
  const thresholds = new Map(geographies.map((geography) => [geography, quantileThresholds(catalog.filter((row) => row.geography === geography).map((row) => row.record_count ?? 0))]));
  const show = (target: Element, key: string, rows: TooltipRow[]) => { cancelClose(); setActive({ position: positionFor(target, 330), key, rows }); };
  const smokeEvidence = (year: number): TooltipRow[] => {
    const annual = modeled.find((row) => row.year === year);
    if (annual) return [
      { label: "Smoke evidence", value: `${formatCompact(annual.population_days)} modeled population-days · ${annual.broad_smoke_days} widespread days` },
      { label: "Worst smoke day", value: `${formatCompact(annual.peak_population_exposed)} residents · ${formatCutoff(annual.peak_date)}` },
    ];
    const operational = recent.find((row) => row.year === year);
    if (operational) return [
      { label: "Smoke evidence", value: `${formatCompact(operational.indicative_population_days)} indicative population-days · ${operational.broad_proxy_days} broad days` },
      { label: "Worst checked day", value: `${formatCompact(operational.peak_indicative_population)} residents${operational.peak_date ? ` · ${formatCutoff(operational.peak_date)}` : ""} · non-comparable screen` },
    ];
    const documented = smokeHistory.find((row) => row.year === year)?.months.flatMap((month) => month.events) ?? [];
    if (documented.length) return [
      { label: "Documented smoke", value: documented.map((event) => event.event).join("; ") },
      { label: "Affected regions", value: [...new Set(documented.map((event) => event.affected_regions))].join("; ") },
    ];
    return [{ label: "Smoke evidence", value: "No comparable national exposure estimate; unknown, not zero" }];
  };
  const details = (row: FireIncidentCatalogYear): TooltipRow[] => {
    const fires = fireContext
      .filter((item) => item.year === row.year && item.geography === row.geography)
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 4);
    return [
      { label: "Year / country", value: `${row.year} · ${row.geography}` },
      { label: "Fire records", value: row.record_count === null ? "No source-covered national catalog" : row.record_count.toLocaleString("en-US") },
      { label: "Recorded acres", value: row.burned_acres === null ? "Not available" : row.burned_acres.toLocaleString("en-US") },
      { label: "Largest records", value: fires.map((fire) => `${fire.fire_name} (${fire.region}, ${formatCompact(fire.acres)} acres)`).join("; ") || "No named large-fire context in the selected source" },
      { label: "Archive scope", value: row.source_scope ? `${row.source_scope}${row.provisional ? " · provisional" : ""}` : row.coverage_status.replaceAll("_", " ") },
      ...smokeEvidence(row.year),
      { label: "Interpretation", value: "Counts follow different archives by country and era; fire records do not prove a U.S. smoke impact" },
    ];
  };

  return (
    <figure className="annual-fire-history" onPointerLeave={scheduleClose} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) scheduleClose(); }}>
      <div className="same-window-heading"><strong>Annual source-covered fire records, 1950–2026</strong><span>within-country count quintiles · exact counts on hover</span></div>
      <div className="annual-fire-chart" style={columnStyle}>
        <div className="annual-fire-row annual-fire-axis-row">
          <span />
          <div className="history-axis">{tickYears.map((year) => <span key={year} style={{ gridColumn: year - firstYear + 1 }}>{year}</span>)}</div>
        </div>
        {geographies.map((geography) => (
          <div className="annual-fire-row" key={geography}>
            <strong>{geography === "United States" ? "U.S." : "Canada"}</strong>
            <div className="annual-fire-cells">
              {years.map((year) => {
                const row = byKey.get(`${geography}-${year}`)!;
                const level = fireRecordLevel(row.record_count, thresholds.get(geography)!);
                const key = `${geography}-${year}`;
                const tooltipRows = details(row);
                return (
                  <span
                    className={`annual-fire-cell level-${level < 0 ? "missing" : level}`}
                    key={year}
                    tabIndex={0}
                    aria-label={`${year}, ${geography}. ${row.record_count === null ? "No source-covered national catalog" : `${row.record_count.toLocaleString("en-US")} source-covered fire records`}.`}
                    aria-describedby={active?.key === key ? id : undefined}
                    onPointerEnter={(event) => show(event.currentTarget, key, tooltipRows)}
                    onPointerOver={(event) => show(event.currentTarget, key, tooltipRows)}
                    onMouseOver={(event) => show(event.currentTarget, key, tooltipRows)}
                    onClick={(event) => show(event.currentTarget, key, tooltipRows)}
                    onFocus={(event) => show(event.currentTarget, key, tooltipRows)}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {active ? <FloatingPanel id={id} position={active.position} className="history-floating-panel" onPointerEnter={cancelClose} onPointerLeave={scheduleClose}><TooltipRows rows={active.rows} /></FloatingPanel> : null}
      <div className="annual-fire-legend">
        <HoverDetail
          className="legend-detail"
          ariaLabel="Annual fire-record grayscale. Hover or focus for details."
          trigger={<span className="legend-detail-trigger"><span>lowest fifth</span>{[1, 2, 3, 4, 5].map((level) => <i className={`annual-fire-cell level-${level}`} key={level} />)}<span>highest fifth · calculated separately by country</span></span>}
        >
          Positive-count years are divided into five equally populated bands within each country. This makes annual variation visible, but U.S. and Canadian shades still cannot be compared directly because their archive scopes differ.
        </HoverDetail>
        <HoverDetail className="legend-detail" trigger={<span className="legend-detail-trigger"><i className="annual-fire-cell level-missing" /><span>no national catalog</span></span>}>Hatching means the controlling source lane has no national incident catalog for that country-year. It is unknown coverage, not zero fires.</HoverDetail>
      </div>
      <figcaption>This is an archive record-density view, not one uniform fire census. Canada uses NFDB from 1950; U.S. coverage begins with MTBS large fires in 1984, broadens to FPA FOD in 1992–2020, then uses a dated InFORM snapshot. Hover any year for the exact count, largest available incidents and smoke evidence.</figcaption>
    </figure>
  );
}

function RecentSmokeEvidence({ allYearSameCutoff = [], fixedPopulation, fireContext }: { allYearSameCutoff?: SmokeSameCutoff[]; fixedPopulation: number; fireContext: FireYearContext[] }) {
  const recentWindow = allYearSameCutoff.filter((row) => row.series_kind === "operational_proxy");
  const currentScreen = recentWindow.find((row) => row.year === 2026)!;
  const previousWindow = recentWindow.find((row) => row.year === 2025)!;
  const rankFor = (key: "population_days" | "peak_population" | "broad_days") => 1 + recentWindow.filter((row) => row[key] > currentScreen[key]).length;
  const burdenRank = rankFor("population_days");
  const peakRank = rankFor("peak_population");
  const broadRank = rankFor("broad_days");
  const burdenLeader = [...recentWindow].sort((a, b) => b.population_days - a.population_days)[0];
  const peakLeader = [...recentWindow].sort((a, b) => b.peak_population - a.peak_population)[0];
  const currentPeakShare = currentScreen.peak_population / fixedPopulation * 100;
  const shareOfPreviousWindow = currentScreen.population_days / previousWindow.population_days * 100;
  const fireNames = (year: number) => fireContext
    .filter((item) => item.year === year)
    .sort((a, b) => b.acres - a.acres)
    .slice(0, 3)
    .map((item) => `${item.fire_name} (${item.region})`)
    .join(", ");
  const comparisonMetrics = [
    { key: "population_days", label: "Indicative population-days", leader: burdenLeader, format: (value: number) => formatCompact(value) },
    { key: "peak_population", label: "Peak daily reach", leader: peakLeader, format: (value: number) => formatCompact(value) },
  ] as const;

  return (
    <section className="operational-block" aria-labelledby="recent-evidence-title">
      <div className="operational-intro">
        <div>
          <h3 id="recent-evidence-title">What the available evidence says about 2026</h3>
          <p>The published wildfire-attribution series above ends in 2023, so it is not used to rank 2026. This section compares every year from 2006–2026 under one separate screen: high PM₂.₅ at ground monitors on days NOAA mapped smoke overhead, always from January 1 through July 18.</p>
        </div>
        <span className="status-label">2026 through {formatCutoff(currentScreen.cutoff)}</span>
      </div>
      <figure className="same-window-overview">
        <div className="same-window-heading"><strong>Same calendar window across all 21 years</strong><span>Jan 1–Jul 18 · monitor + satellite screen only</span></div>
        <div className="same-window-kpis">
          <HoverDetail className="same-window-kpi" trigger={<span><strong>{formatRank(burdenRank)}</strong><b>burden rank</b><small>of {recentWindow.length} years</small></span>}>2026 recorded {currentScreen.population_days.toLocaleString("en-US")} indicative population-days. {burdenLeader.year} ranked first with {burdenLeader.population_days.toLocaleString("en-US")}.</HoverDetail>
          <HoverDetail className="same-window-kpi" trigger={<span><strong>{formatRank(peakRank)}</strong><b>peak-reach rank</b><small>of {recentWindow.length} years</small></span>}>The 2026 peak reached {currentScreen.peak_population.toLocaleString("en-US")} indicative residents on {formatCutoff(currentScreen.peak_date)}. {peakLeader.year} ranked first.</HoverDetail>
          <HoverDetail className="same-window-kpi" trigger={<span><strong>{currentScreen.broad_days}</strong><b>days reaching 10M+</b><small>{formatRank(broadRank)} by annual count</small></span>}>A broad day is one when qualifying monitored counties contained at least 10 million fixed residents at once.</HoverDetail>
        </div>
        <div className="same-window-chart">
          {comparisonMetrics.map((metric) => {
            const maximum = Math.max(...recentWindow.map((row) => row[metric.key]));
            return (
              <div className="same-window-metric" key={metric.key}>
                <div className="same-window-metric-label"><strong>{metric.label}</strong><span>2026 · {metric.format(currentScreen[metric.key])}</span></div>
                <div className="same-window-year-grid">
                  {recentWindow.map((row) => {
                    const value = row[metric.key];
                    const leader = row.year === metric.leader.year;
                    return (
                      <HoverDetail
                        key={`${metric.key}-${row.year}`}
                        className={`same-window-year${row.year === 2026 ? " current" : ""}${leader ? " leader" : ""}`}
                        ariaLabel={`${row.year}: ${value.toLocaleString("en-US")} ${metric.label.toLowerCase()} through July 18`}
                        style={{ "--window-height": `${Math.max(2, value / maximum * 100)}%` } as CSSProperties}
                        trigger={<span><i /><small>{String(row.year).slice(2)}</small></span>}
                      >
                        <TooltipRows rows={[{ label: "Period", value: `Jan 1–${formatMonthDay(row.cutoff)}, ${row.year}` }, { label: metric.label, value: value.toLocaleString("en-US") }, { label: "Peak", value: `${row.peak_population.toLocaleString("en-US")} · ${formatCutoff(row.peak_date)}` }, { label: "Days reaching 10M+", value: row.broad_days.toLocaleString("en-US") }, { label: "Event context", value: fireNames(row.year) || "No source-covered named fire record" }, { label: "Method", value: row.series_label }]} />
                      </HoverDetail>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
        <div className="same-window-legend"><span><i className="ordinary" />other years</span><span><i className="leader" />highest year</span><span><i className="current" />2026</span></div>
        <figcaption>2026 ranks {formatRank(burdenRank)} for cumulative burden and {formatRank(peakRank)} for peak daily reach. {burdenLeader.year} remains higher on both measures. Values are comparable within this screen only, not with the Stanford modeled series.</figcaption>
      </figure>
      <p className="operational-takeaway"><HoverDetail className="metric-hover" ariaLabel="2026 same-window smoke comparison. Hover or focus for exact values." trigger={<span><strong>2026 is already an outlier under the same-window screen.</strong> Its {formatCompact(currentScreen.population_days)} indicative population-days exceed 2025 by {(shareOfPreviousWindow - 100).toFixed(0)}%; its {formatCompact(currentScreen.peak_population)}-resident peak reached about {currentPeakShare.toFixed(0)}% of the fixed contiguous population. {burdenLeader.year} remains the leader.</span>}><TooltipRows rows={recentWindow.map((row) => ({ label: String(row.year), value: `${row.population_days.toLocaleString("en-US")} indicative population-days · peak ${row.peak_population.toLocaleString("en-US")} on ${formatCutoff(row.peak_date)} · ${row.broad_days} broad days` }))} /></HoverDetail></p>
      <p className="news-context">The <a href={WASHINGTON_POST_URL} target="_blank" rel="noreferrer">Washington Post reported →</a> D.C. reached <AqiBadge value={175} /> between 4 and 5 a.m. on July 18—the <HoverDetail className="inline-metric-hover" ariaLabel="30th consecutive hour. Hover or focus for report context." trigger={<strong>30th consecutive hour</strong>}>The Washington Post’s July 18 report described D.C. as remaining in unhealthy or very unhealthy territory for 30 consecutive hours. This reported local episode is not an input to the national annual model.</HoverDetail> in unhealthy or very unhealthy territory. This episode is context, not an input to the annual model.</p>
    </section>
  );
}

function BurnedAreaChart({ unitedStates, canada, current, fireContext }: { unitedStates: AnnualFire[]; canada: AnnualFire[]; current: CurrentFireActivity[]; fireContext: FireYearContext[] }) {
  const canadaRows = canada.filter((row) => row.year <= 2025 && !row.provisional);
  const usRows = unitedStates.filter((row) => row.year <= 2024 && !row.provisional);
  const currentByGeography = new Map(current.map((row) => [row.geography, row]));
  const canadaCurrent = currentByGeography.get("Canada")!;
  const usCurrent = currentByGeography.get("United States")!;
  const currentDate = usCurrent.as_of_date;
  const currentMonthDay = formatMonthDay(currentDate);
  const annualRows = (row: AnnualFire, geography: FireYearContext["geography"], sourceStatus: string): TooltipRow[] => {
    const records = fireContext
      .filter((item) => item.year === row.year && item.geography === geography && !item.provisional)
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 4);
    return [
      { label: "Date", value: String(row.year) },
      { label: "Event", value: records.map((item) => item.fire_name).join(", ") || "No source-covered named record" },
      { label: "Fire regions", value: [...new Set(records.map((item) => item.region))].join(", ") || "Not available" },
      { label: "Source / status", value: sourceStatus },
      { label: "Largest records", value: records.map((item) => `${item.fire_name} ${formatCompact(item.acres)} acres`).join(", ") || "Not available" },
      { label: "Attribution", value: "Fire activity context, not smoke-source attribution" },
    ];
  };

  return (
    <figure className="fire-combined-chart">
      <div className="figure-heading">
        <div><h3>Canada and United States burned area</h3><p>Annual acres · complete historical series plus {formatCutoff(currentDate)} YTD markers</p></div>
      </div>
      <InteractiveLineChart
        series={[
          { key: "canada", label: "Canada · NBAC", color: "#1B365D", points: canadaRows.map((row) => ({ year: row.year, value: row.acres_burned, metricLabel: "Burned acres", rows: annualRows(row, "Canada", "NRCan NBAC · complete annual adjusted area") })), legendRows: [{ label: "Source", value: "NRCan National Burned Area Composite" }, { label: "Measure", value: "Adjusted complete-year burned area across Canada" }] },
          { key: "united-states", label: "U.S. · MTBS large fires", color: "#9A4B36", dash: "5 3", openPoints: true, points: usRows.map((row) => ({ year: row.year, value: row.acres_burned, metricLabel: "Burned acres", rows: annualRows(row, "United States", "MTBS · complete annual mapped large-fire area") })), legendRows: [{ label: "Source", value: "Monitoring Trends in Burn Severity" }, { label: "Measure", value: "Mapped large-fire area; not all reported U.S. fires" }] },
        ]}
        supplementalPoints={[
          { year: 2026, value: canadaCurrent.burned_area_acres, metricLabel: "Burned acres YTD", seriesKey: "canada", label: "Canada", color: "#1B365D", rows: [{ label: "Date", value: `Jan 1–${currentMonthDay}, 2026` }, { label: "Event", value: fireContext.filter((item) => item.year === 2026 && item.geography === "Canada").slice(0, 4).map((item) => item.fire_name).join(", ") || "Current fire season" }, { label: "Fire regions", value: [...new Set(fireContext.filter((item) => item.year === 2026 && item.geography === "Canada").slice(0, 4).map((item) => item.region))].join(", ") || "Not available" }, { label: "Source / status", value: "NRCan CWFIF · preliminary year-to-date" }, { label: "Reported fires", value: canadaCurrent.fire_count.toLocaleString("en-US") }] },
          { year: 2026, value: usCurrent.burned_area_acres, metricLabel: "Burned acres YTD", seriesKey: "united-states", label: "United States", color: "#9A4B36", rows: [{ label: "Date", value: `Jan 1–${currentMonthDay}, 2026` }, { label: "Event", value: fireContext.filter((item) => item.year === 2026 && item.geography === "United States").slice(0, 4).map((item) => item.fire_name).join(", ") || "Current fire season" }, { label: "Fire regions", value: [...new Set(fireContext.filter((item) => item.year === 2026 && item.geography === "United States").slice(0, 4).map((item) => item.region))].join(", ") || "Not available" }, { label: "Source / status", value: "NIFC · preliminary year-to-date" }, { label: "Reported fires", value: usCurrent.fire_count.toLocaleString("en-US") }] },
        ]}
        maximum={40_000_000}
        tickYears={[1972, 1980, 1990, 2000, 2010, 2020, 2026]}
        ariaLabel="Annual burned area in Canada and the United States, with preliminary 2026 year-to-date markers"
        height={206}
      />
      <figcaption>Canada: NBAC adjusted annual area, 1972–2025. United States: MTBS mapped large wildfires, 1984–2024. The 2026 markers use current operational totals through {currentMonthDay} and are deliberately not connected to either complete-year line.</figcaption>
    </figure>
  );
}

const NORTH_AMERICA_PIXEL_MASK = [
  "......#####........",
  "....########.......",
  "..############.....",
  ".##############....",
  "################...",
  "..###############..",
  "...#############...",
  "....#########......",
  "......#####........",
  ".......###.........",
];

const FIRE_DENSITY_COLORS = ["#f1f0eb", "#deddd7", "#c3c2bc", "#92918b", "#5d5c58", "#242422"];

function densityRangeLabels(thresholds: number[]) {
  if (thresholds.length !== 5) return ["Lowest", "Low", "Moderate", "Elevated", "High", "Highest"];
  const compact = (value: number) => formatCompact(value, value >= 1_000_000 ? 2 : 1);
  return [
    `≤${compact(thresholds[0])}`,
    `${compact(thresholds[0])}–${compact(thresholds[1])}`,
    `${compact(thresholds[1])}–${compact(thresholds[2])}`,
    `${compact(thresholds[2])}–${compact(thresholds[3])}`,
    `${compact(thresholds[3])}–${compact(thresholds[4])}`,
    `>${compact(thresholds[4])}`,
  ];
}

function FireDensityMap({ tiles = [], scale }: { tiles?: FireDensityTile[]; scale?: FireDensityScale }) {
  if (!tiles.length) {
    return (
      <figure className="fire-density-figure density-unavailable">
        <div className="same-window-heading"><strong>North American fire density</strong><span>spatial aggregate pending</span></div>
        <HoverDetail
          className="density-placeholder-hover"
          ariaLabel="Fire-density map data requirements"
          trigger={(
            <span className="density-placeholder-grid" style={{ "--density-columns": NORTH_AMERICA_PIXEL_MASK[0].length } as CSSProperties}>
              {NORTH_AMERICA_PIXEL_MASK.flatMap((row, y) => [...row].map((cell, x) => cell === "#" ? <i key={`${x}-${y}`} style={{ gridColumn: x + 1, gridRow: y + 1 }} /> : null))}
              <b>Spatial density data not yet generated</b>
            </span>
          )}
        >
          The existing website contract has annual national totals and text-only fire regions, but no coordinates or grid-cell aggregates. A density tile needs grid x/y, period, fire count, burned acres, geography labels and source IDs.
        </HoverDetail>
        <figcaption>Scaffold only—no density is encoded. Required contract: <code>x, y, year_start, year_end, fire_count, burned_acres, geographies, label, source_ids</code> on one documented North America grid.</figcaption>
      </figure>
    );
  }

  const columns = Math.max(...tiles.map((tile) => tile.x)) + 1;
  const rows = Math.max(...tiles.map((tile) => tile.y)) + 1;
  const mappedRecords = tiles.reduce((total, tile) => total + tile.fire_count, 0);
  const geographies = [...new Set(tiles.flatMap((tile) => tile.geographies))];
  const northAmericaComplete = geographies.includes("United States") && geographies.includes("Canada");
  const periods = [...new Set(tiles.map((tile) => `${tile.year_start}–${tile.year_end}`))].join(", ");
  const rangeLabels = densityRangeLabels(scale?.thresholds ?? []);
  return (
    <figure className="fire-density-figure">
      <div className="same-window-heading"><strong>Where reported burned area concentrates</strong><span>{formatCompact(mappedRecords, 2)} georeferenced records · {northAmericaComplete ? "U.S. + Canada" : `${geographies.join(" + ")} coverage only`} · {periods}</span></div>
      {scale ? (
        <p className="density-insight"><HoverDetail className="metric-hover" trigger={<span><strong>{scale.top_decile_share_percent}%</strong> of reported burned acres fall in the darkest 10% of occupied grid cells.</span>}><TooltipRows rows={[
          { label: "Darkest cells", value: `${scale.top_decile_cell_count.toLocaleString("en-US")} occupied grid cells` },
          { label: "Share of acres", value: `${scale.top_decile_share_percent}% of all source-covered burned acres in the shared-period grid` },
          { label: "Classification", value: "Distribution quantiles of reported burned acres per occupied grid cell" },
        ]} /></HoverDetail></p>
      ) : null}
      <div className="density-grid" style={{ "--density-columns": columns, "--density-rows": rows } as CSSProperties}>
        {tiles.map((tile) => (
          <HoverDetail
            className="density-tile-trigger"
            key={`${tile.x}-${tile.y}-${tile.year_start}-${tile.year_end}`}
            ariaLabel={`${tile.label}: ${tile.burned_acres.toLocaleString("en-US")} burned acres across ${tile.fire_count.toLocaleString("en-US")} fires`}
            style={{ gridColumn: tile.x + 1, gridRow: tile.y + 1, "--tile-color": FIRE_DENSITY_COLORS[tile.level ?? 0] } as CSSProperties}
            trigger={<span className="density-tile" />}
          >
            <TooltipRows rows={[
              { label: "Tile", value: tile.label },
              { label: "Period", value: `${tile.year_start}–${tile.year_end}` },
              { label: "Fire count", value: tile.fire_count.toLocaleString("en-US") },
              { label: "U.S. records", value: (tile.us_fire_count ?? 0).toLocaleString("en-US") },
              { label: "Canadian records", value: (tile.canada_fire_count ?? 0).toLocaleString("en-US") },
              { label: "Burned acres", value: tile.burned_acres.toLocaleString("en-US") },
              { label: "Map band", value: rangeLabels[tile.level ?? 0] },
              { label: "Geographies", value: tile.geographies.join(", ") },
              { label: "Sources", value: tile.source_ids.map((id) => id === "usfs-fpa-fod-1992-2020" ? "USFS FPA FOD" : id === "nrcan-nfdb-all-fire-points-2026-06-08" ? "NRCan NFDB" : id).join(", ") },
              { label: "Coverage", value: tile.coverage_note ?? "Source-covered records; reporting coverage varies" },
            ]} />
          </HoverDetail>
        ))}
      </div>
      <div className="density-scale" aria-label="Reported burned acres per occupied grid cell">
        <span className="density-scale-title">Reported burned acres per cell</span>
        <div className="density-scale-bands">
          {rangeLabels.map((label, level) => (
            <HoverDetail
              className="density-scale-detail"
              key={label}
              ariaLabel={`Map band ${label}. Hover or focus for details.`}
              trigger={<span className="density-scale-band"><i style={{ background: FIRE_DENSITY_COLORS[level] }} /><b>{label}</b></span>}
            >
              <TooltipRows rows={[
                { label: "Band", value: `${level + 1} of ${rangeLabels.length}` },
                { label: "Burned acres", value: label },
                { label: "Metric", value: "Source-covered reported burned acres in one occupied grid cell, 1992–2020" },
              ]} />
            </HoverDetail>
          ))}
        </div>
      </div>
      <figcaption>Six distribution-aware bands preserve contrast from the lowest cells through the highest-decile cells; hover any cell for exact acres and incidents. The map combines U.S. FPA FOD and Canadian NFDB records over their shared 1992–2020 period. Counts are not compared across countries because reporting coverage differs.</figcaption>
    </figure>
  );
}

function Method() {
  const steps: { number: string; title: string; input: ReactNode; operation: ReactNode; output: ReactNode }[] = [
    {
      number: "1",
      title: "Begin with one wildfire-smoke estimate per county-day",
      input: <>Stanford ECHO v2 beta daily county predictions, 2006–2023.</>,
      operation: <>The Stanford model combines ground monitors, NOAA satellite smoke plumes, weather, fire and land variables to estimate the PM₂.₅ attributable to wildfire smoke—separate from other pollution.</>,
      output: <><a href={`${GITHUB_RAW_DATA_URL}/stanford_daily_smoke_2006_2023.csv`} target="_blank" rel="noreferrer">Daily county-derived output →</a> with date, qualifying population and national exposure totals.</>,
    },
    {
      number: "2",
      title: "Apply the same high-smoke rule to every county-day",
      input: <>Modeled wildfire-attributable PM₂.₅ and county GEOID.</>,
      operation: <>Mark a county-day as high smoke when <code>smoke PM₂.₅ ≥ 35.5 µg/m³</code>. That concentration is the lower PM₂.₅ breakpoint for <AqiBadge value={101} />; the calculation applies it to the wildfire-only increment, not total-air AQI.</>,
      output: <>A binary high-smoke flag for each county and date. The threshold does not change between years.</>,
    },
    {
      number: "3",
      title: "Attach a fixed population to qualifying counties",
      input: <>July 1, 2020 Census county population joined by GEOID.</>,
      operation: <>A qualifying county contributes its full fixed population for that day; a non-qualifying county contributes zero. Holding population constant keeps population growth and migration from manufacturing a trend.</>,
      output: <><code>county population exposed = high-smoke flag × fixed 2020 population</code>.</>,
    },
    {
      number: "4",
      title: "Aggregate people across dates, then summarize each year",
      input: <>All qualifying county populations for every date in a calendar year.</>,
      operation: <>Sum county populations by date, then sum those daily totals across the year for person-days. Record the yearly maximum daily exposure and count a widespread smoke day when at least 10 million residents qualify at once.</>,
      output: <><a href={`${GITHUB_RAW_DATA_URL}/stanford_annual_smoke_2006_2023.csv`} target="_blank" rel="noreferrer">Annual metric output →</a> with person-days, widespread days, annual reach and peak population exposed.</>,
    },
  ];
  return (
    <div className="method-body">
      <p className="method-lede">The headline metric answers one question: <strong>How many people encountered a high wildfire-smoke increment, and for how many days?</strong></p>
      <div className="method-steps">
        {steps.map((step) => (
          <article key={step.number}>
            <span>{step.number}</span>
            <div>
              <h3>{step.title}</h3>
              <dl>
                <div><dt>Input</dt><dd>{step.input}</dd></div>
                <div><dt>Calculation</dt><dd>{step.operation}</dd></div>
                <div><dt>Output</dt><dd>{step.output}</dd></div>
              </dl>
            </div>
          </article>
        ))}
      </div>
      <ol className="method-notes" aria-label="Method terms and caveats">
        <li><strong>Person-days of unhealthy smoke air.</strong> The formal unit remains population-days: ten people exposed for one day and one person exposed for ten days both equal ten person-days.</li>
        <li><strong>Days per person.</strong> Annual person-days divided by the fixed 327,345,959-resident population. It is a national average burden, not proof that every resident experienced the average.</li>
        <li><strong>Share reached at least once.</strong> Fixed residents of any county that crossed the threshold on one or more days, divided by the same fixed population. Residence is not daily movement.</li>
        <li><strong>Widespread smoke day.</strong> Counties containing at least 10 million fixed residents crossed the threshold at once.</li>
        <li><strong>Severe smoke day.</strong> A sensitivity threshold: modeled wildfire-smoke PM₂.₅ reached at least 50 µg/m³ in counties containing 10 million or more residents.</li>
        <li><strong>Benchmark and streaks.</strong> The benchmark is the worst modeled daily reach in 2006–2010. A streak counts adjacent calendar days that each meet the widespread-day rule; missing dates break a streak.</li>
        <li><strong>Threshold, not a literal wildfire AQI.</strong> Total-air <AqiBadge value={101} label="AQI" /> includes every pollution source. This project applies the same concentration breakpoint to the modeled wildfire-only increment.</li>
        <li><strong>Comparable series begins in 2006.</strong> Earlier decades lack the same national PM₂.₅ monitoring and daily satellite smoke record. Documented historical episodes are shown as context and are never backfilled as modeled exposure.</li>
      </ol>
    </div>
  );
}

function SourceList({ sources }: { sources: SourceRecord[] }) {
  return (
    <ol className="reference-list source-list">
      {sources.map((source) => (
        <li key={source.id}>
          <span>{source.organization}. <strong>{source.title}</strong>. {source.coverage}.</span>
          <div className="source-actions">
            <a href={source.url} target="_blank" rel="noreferrer">Original source →</a>
            {source.retrieval_url ? <a href={source.retrieval_url} target="_blank" rel="noreferrer">{source.retrieval_url.includes("YYYYMMDD") ? "Daily-file pattern →" : "Direct data ↓"}</a> : null}
          </div>
          <small>{source.role}</small>
        </li>
      ))}
    </ol>
  );
}

function Sources({ sources, researchPapers }: { sources: SourceRecord[]; researchPapers: ResearchPaper[] }) {
  const originalSources = sources.filter((source) => !CONTEXT_SOURCE_IDS.has(source.id));
  const contextSources = sources.filter((source) => CONTEXT_SOURCE_IDS.has(source.id));
  return (
    <div className="sources-body">
      <p className="data-availability">Every original input, exact publisher file or feed, research paper, and project-generated table is linked below. The <a href={publicPath("/data/source_manifest.json")} target="_blank" rel="noreferrer">machine-readable source manifest →</a> preserves retrieval dates, checksums, licenses and comparability notes; the <a href={GITHUB_URL} target="_blank" rel="noreferrer">repository →</a> contains the complete processing and validation code.</p>
      <h3>Original data sources</h3>
      <p className="source-group-note">Use “Original source” for the publisher’s documentation and “Direct data” for the exact file, API, archive, or feed used by the project.</p>
      <SourceList sources={originalSources} />
      <h3>Research and methodology papers</h3>
      <ol className="reference-list paper-list">
        {researchPapers.map((paper) => (
          <li key={paper.id}>
            <span><strong>{paper.title}</strong>. {paper.citation}</span>
            <div className="source-actions">
              <a href={paper.url} target="_blank" rel="noreferrer">Paper →</a>
              {paper.download_url ? <a href={paper.download_url} target="_blank" rel="noreferrer">PDF ↓</a> : null}
              <em>{paper.status}</em>
            </div>
            <small>{paper.role}</small>
          </li>
        ))}
      </ol>
      <h3>Project data downloads</h3>
      <ol className="dataset-list">
        {DATASETS.map(([title, href, note]) => <li key={href}><a href={href} download>{title} ↓</a><span>{note}</span></li>)}
      </ol>
      <h3>Historical and interpretive context</h3>
      <p className="source-group-note">These records document episodes, reporting, or health analogies. They do not control the comparable annual exposure calculation.</p>
      <SourceList sources={contextSources} />
    </div>
  );
}

export default function Dashboard({ initialData }: { initialData: DashboardData }) {
  const currentByGeography = new Map(initialData.current_fire_activity.map((row) => [row.geography, row]));
  const usCurrent = currentByGeography.get("United States");
  const canadaCurrent = currentByGeography.get("Canada");
  if (!usCurrent || !canadaCurrent) throw new Error("Current July 2026 fire inputs are missing");
  const trend = initialData.smoke_trend;
  const firstSmokeYear = initialData.annual_smoke[0];
  const smoke2023 = initialData.annual_smoke.find((row) => row.year === 2023)!;
  const earlyWidespreadDays = initialData.annual_smoke.filter((row) => row.year <= 2015).reduce((sum, row) => sum + row.broad_smoke_days, 0);
  const recentWidespreadDays = initialData.annual_smoke.filter((row) => row.year >= 2016).reduce((sum, row) => sum + row.broad_smoke_days, 0);
  const fixedPopulationCaveat = "County-average modeled increment; fixed July 1, 2020 population; residence, not daily movement.";
  const decoupling = initialData.fire_smoke_decoupling;
  const canadaMultiple = initialData.fire_trends.canada.recent_average_acres / initialData.fire_trends.canada.first_average_acres;
  const usMultiple = initialData.fire_trends.united_states.recent_average_acres / initialData.fire_trends.united_states.first_average_acres;
  const commonCutoff = initialData.meta.operational_proxy_as_of_date;
  const currentFireMonthDay = formatMonthDay(usCurrent.as_of_date);

  return (
    <main className="paper">
      <header className="hero">
        <div className="hero-meta"><p className="kicker">Modeling wildfire smoke air quality impact trendline</p><PrintButton /></div>
        <h1>How wildfire smoke exposure has changed across the United States</h1>
        <p className="hero-lede">This model estimates how many U.S. residents encountered wildfire-smoke PM₂.₅ high enough that the air would be unhealthy for sensitive groups from smoke alone—crossing the <AqiBadge value={101} label="AQI 101 threshold" treatment="threshold" />. Canadian smoke is included whenever it reached U.S. counties.</p>
        <p className="as-of-line">Comparable model: 2006–2023 · preliminary smoke and fire updates through {formatCutoff(commonCutoff)}</p>
      </header>

      <section className="lead-section" aria-label="Long-run smoke trend summary">
        <div className="lead-metrics">
          <LeadMetric value={`${Math.round(smoke2023.share_exposed_at_least_once)}%`} label="of Americans breathed unhealthy smoke in 2023" explanation={`${formatCompact(smoke2023.residents_exposed_at_least_once, 0)} residents had at least one qualifying day`} tooltip={`${smoke2023.residents_exposed_at_least_once.toLocaleString("en-US")} residents, or ${smoke2023.share_exposed_at_least_once.toFixed(1)}% of ${trend.fixed_population.toLocaleString("en-US")}. ${fixedPopulationCaveat}`} />
          <LeadMetric value={`${earlyWidespreadDays} → ${recentWidespreadDays}`} label="widespread smoke days, then vs now" explanation="10M+ residents at once · 2006–15 vs 2016–23" tooltip={`${earlyWidespreadDays} widespread smoke day in 2006–2015, compared with ${recentWidespreadDays} in 2016–2023. ${fixedPopulationCaveat}`} />
          <LeadMetric value={`${firstSmokeYear.counties_exposed_at_least_once.toLocaleString("en-US")} → ${smoke2023.counties_exposed_at_least_once.toLocaleString("en-US")}`} label="counties touched at least once per year" explanation="more than half of 3,108 counties qualified in 2023" tooltip={`${firstSmokeYear.counties_exposed_at_least_once} counties in 2006 versus ${smoke2023.counties_exposed_at_least_once.toLocaleString("en-US")} in 2023 (${(smoke2023.counties_exposed_at_least_once / 3108 * 100).toFixed(1)}%). ${fixedPopulationCaveat}`} />
          <LeadMetric value="1 in 4" label="Americans on the single worst day" explanation={`${formatCutoff(smoke2023.peak_date)} · ${formatCompact(smoke2023.peak_population_exposed)} residents`} tooltip={`${smoke2023.peak_population_exposed.toLocaleString("en-US")} residents, or ${(smoke2023.peak_population_exposed / trend.fixed_population * 100).toFixed(1)}% of the fixed population—the largest modeled daily reach. ${fixedPopulationCaveat}`} />
        </div>
        <HoverDetail
          className="burden-callout"
          ariaLabel={`${trend.recent_to_early_multiplier.toFixed(1)} times higher recent smoke burden. Hover or focus for the periods and exact averages.`}
          trigger={<span><strong>{trend.recent_to_early_multiplier.toFixed(1)}× higher recent burden.</strong><span>The last five comparable years averaged more than nine times the population-days of the first five.</span></span>}
        >
          <TooltipRows rows={[
            { label: trend.early_period, value: `${trend.early_average_population_days.toLocaleString("en-US")} average population-days · ${trend.early_per_capita_days.toFixed(2)} days per fixed resident` },
            { label: trend.recent_period, value: `${trend.recent_average_population_days.toLocaleString("en-US")} average population-days · ${trend.recent_per_capita_days.toFixed(2)} days per fixed resident` },
            { label: "Ratio", value: `${trend.recent_to_early_multiplier.toFixed(1)}× · comparable Stanford model only` },
          ]} />
        </HoverDetail>
      </section>

      <section className="report-section" aria-labelledby="trend-title">
        <div className="section-heading"><span>01</span><div><h2 id="trend-title">The modeled smoke trend</h2><p>Comparable nationwide estimates begin in 2006; current conditions remain a separate preliminary series</p></div></div>
        <p className="section-insight"><HoverDetail className="metric-hover" ariaLabel="Per-person smoke burden comparison. Hover or focus for exact values." trigger={<span>Averaged across the country, the typical American now lives through about three-quarters of a day of unhealthy wildfire smoke per year—roughly one day every 16 months, up from about one every 12 years in the late 2000s.</span>}><TooltipRows rows={[
          { label: trend.early_period, value: `${trend.early_per_capita_days.toFixed(2)} days per fixed resident · ${trend.early_average_population_days.toLocaleString("en-US")} average population-days` },
          { label: trend.recent_period, value: `${trend.recent_per_capita_days.toFixed(2)} days per fixed resident · ${trend.recent_average_population_days.toLocaleString("en-US")} average population-days` },
          { label: "Change", value: `${trend.recent_to_early_multiplier.toFixed(1)}× higher recent average burden` },
        ]} /></HoverDetail></p>
        <SmokeTrendChart data={initialData.annual_smoke} trend={trend} extremes={initialData.extremes} fireContext={initialData.fire_year_context} regionContext={initialData.smoke_region_context} />
        <WorstDays extremes={initialData.extremes} fireContext={initialData.fire_year_context} regionContext={initialData.smoke_region_context} />
        <SmokeHistory rows={initialData.smoke_history} fireRows={initialData.fire_history} observationCutoff={commonCutoff} fireContext={initialData.fire_year_context} regionContext={initialData.smoke_region_context} />
        <AnnualFireRecordHistory catalog={initialData.fire_incident_catalog} smokeHistory={initialData.smoke_history} modeled={initialData.annual_smoke} recent={initialData.operational_proxy} fireContext={initialData.fire_year_context} />
        <SeasonalityAndRegions seasonality={initialData.seasonality} regionalShift={initialData.regional_shift} regionContext={initialData.smoke_region_context} />
        <RecentSmokeEvidence allYearSameCutoff={initialData.smoke_same_cutoff} fixedPopulation={trend.fixed_population} fireContext={initialData.fire_year_context} />
      </section>

      <section className="report-section" aria-labelledby="fire-trend-title">
        <div className="section-heading"><span>02</span><div><h2 id="fire-trend-title">Historical burned-area trendlines</h2><p>Complete annual Canadian burned area and mapped U.S. large-fire area, with current 2026 totals kept as separate markers</p></div></div>
        <BurnedAreaChart unitedStates={initialData.annual_fire} canada={initialData.annual_canada_fire ?? []} current={initialData.current_fire_activity} fireContext={initialData.fire_year_context} />
      </section>

      <section className="report-section" aria-labelledby="fire-title">
        <div className="section-heading"><span>03</span><div><h2 id="fire-title">North American fire seasons now burn more land</h2><p><HoverDetail className="inline-data-detail" ariaLabel="Historical fire-season comparison. Hover or focus for exact period averages." trigger={<span>Canada’s recent decade averaged {canadaMultiple.toFixed(1)}× its 1970s baseline; U.S. mapped large fires averaged {usMultiple.toFixed(1)}× their 1980s baseline</span>}><TooltipRows rows={[
          { label: "Canada", value: `${initialData.fire_trends.canada.first_period}: ${formatCompact(initialData.fire_trends.canada.first_average_acres)} average acres · ${initialData.fire_trends.canada.recent_period}: ${formatCompact(initialData.fire_trends.canada.recent_average_acres)}` },
          { label: "United States", value: `${initialData.fire_trends.united_states.first_period}: ${formatCompact(initialData.fire_trends.united_states.first_average_acres)} average acres · ${initialData.fire_trends.united_states.recent_period}: ${formatCompact(initialData.fire_trends.united_states.recent_average_acres)}` },
        ]} /></HoverDetail></p></div></div>
        <p className="section-insight">More burned land increases the amount of smoke available for transport. The exposure result still varies sharply with wind direction: a Canadian fire season can produce a large U.S. burden even when U.S. acreage is comparatively low.</p>
        <FireDensityMap tiles={initialData.fire_density_tiles} scale={initialData.fire_density_scale} />
        <div className="fire-summary">
          <div><HoverDetail className="metric-hover" trigger={<span className="fire-metric-trigger"><strong>{canadaMultiple.toFixed(1)}×</strong><span>Canada recent decade vs 1972–1981</span></span>}>{initialData.fire_trends.canada.recent_period} averaged {formatCompact(initialData.fire_trends.canada.recent_average_acres)} acres—{initialData.fire_trends.canada.percent_change}% more than {formatCompact(initialData.fire_trends.canada.first_average_acres)} in {initialData.fire_trends.canada.first_period}.</HoverDetail></div>
          <div><HoverDetail className="metric-hover" trigger={<span className="fire-metric-trigger"><strong>{usMultiple.toFixed(1)}×</strong><span>U.S. recent decade vs 1984–1993</span></span>}>{initialData.fire_trends.united_states.recent_period} averaged {formatCompact(initialData.fire_trends.united_states.recent_average_acres)} acres—{initialData.fire_trends.united_states.percent_change}% more than {formatCompact(initialData.fire_trends.united_states.first_average_acres)} in {initialData.fire_trends.united_states.first_period}.</HoverDetail></div>
          <div><HoverDetail className="metric-hover" trigger={<span className="fire-metric-trigger"><strong>{formatCompact(canadaCurrent.burned_area_acres, 2)}</strong><span>Canada · Jan 1–{currentFireMonthDay}, 2026</span></span>}>{canadaCurrent.fire_count.toLocaleString("en-US")} fires reported by NRCan CWFIF; preliminary year-to-date total.</HoverDetail></div>
          <div><HoverDetail className="metric-hover" trigger={<span className="fire-metric-trigger"><strong>{formatCompact(usCurrent.burned_area_acres, 2)}</strong><span>U.S. · Jan 1–{currentFireMonthDay}, 2026</span></span>}>{usCurrent.fire_count.toLocaleString("en-US")} fires reported by NIFC; preliminary year-to-date total.</HoverDetail></div>
        </div>
        <p className="operational-takeaway fire-decoupling"><strong>2023 broke the exposure record without a large U.S. fire year.</strong> U.S. mapped burned area was <HoverDetail className="inline-metric-hover" trigger={<span>{Math.abs(decoupling.us_change_vs_average_percent)}% below</span>}>{formatCompact(decoupling.us_mtbs_acres)} acres in 2023 versus a {formatCompact(decoupling.us_mtbs_2013_2022_average_acres)}-acre 2013–2022 average.</HoverDetail> its preceding-decade average, while Canada recorded <HoverDetail className="inline-metric-hover" trigger={<span>{decoupling.canada_multiple_of_average.toFixed(1)}×</span>}>{formatCompact(decoupling.canada_nbac_acres)} acres in 2023 versus a {formatCompact(decoupling.canada_nbac_2013_2022_average_acres)}-acre 2013–2022 average.</HoverDetail> its average. Documented June 2023 episodes traced the smoke to Canadian fires; this is documented co-occurrence, not model-derived plume attribution.</p>
        <p className="fire-context">A <BenNollGraphicLink>Washington Post graphic shared by Ben Noll →</BenNollGraphicLink> shows Canada’s largest 1972–2025 fire seasons clustering among warmer May–September years. That relationship explains rising fire potential; the smoke-exposure model above measures who was actually reached.</p>
      </section>

      <section className="report-section" aria-labelledby="method-title">
        <div className="section-heading"><span>04</span><div><h2 id="method-title">How the numbers are calculated</h2><p>The same threshold and fixed population are applied to every comparable year</p></div></div>
        <Method />
      </section>

      <section className="report-section sources-section" aria-labelledby="sources-title">
        <div className="section-heading"><span>05</span><div><h2 id="sources-title">Sources, papers and downloads</h2><p>Original publisher records, cited research and reproducible outputs</p></div></div>
        <Sources sources={initialData.sources} researchPapers={initialData.research_papers} />
      </section>

      <footer className="site-footer">
        <span>by <a href={X_URL} target="_blank" rel="noreferrer">Daniel →</a></span>
        <nav aria-label="Footer links"><a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub →</a></nav>
      </footer>
    </main>
  );
}
