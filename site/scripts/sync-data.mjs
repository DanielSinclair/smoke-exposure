import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";


const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const copies = [
  ["../data/processed/dashboard.json", "public/data/dashboard.json"],
  ["../data/processed/current_fire_activity_2026.csv", "public/data/current_fire_activity_2026.csv"],
  ["../data/processed/large_fire_incidents_source_covered.csv", "public/data/large_fire_incidents_source_covered.csv"],
  ["../data/processed/large_fire_incidents_annual_source_covered.csv", "public/data/large_fire_incidents_annual_source_covered.csv"],
  ["../data/processed/all_fire_incidents_annual_source_covered.csv", "public/data/all_fire_incidents_annual_source_covered.csv"],
  ["../data/processed/fire_incidents_monthly_source_covered.csv", "public/data/fire_incidents_monthly_source_covered.csv"],
  ["../data/processed/fire_incidents_annual_catalog_1950_2026.csv", "public/data/fire_incidents_annual_catalog_1950_2026.csv"],
  ["../data/processed/fire_incident_catalog_sources.csv", "public/data/fire_incident_catalog_sources.csv"],
  ["../data/processed/all_fire_density_tiles_1992_2020.csv", "public/data/all_fire_density_tiles_1992_2020.csv"],
  ["../data/processed/fire_year_context.csv", "public/data/fire_year_context.csv"],
  ["../data/processed/smoke_region_context_2006_2023.csv", "public/data/smoke_region_context_2006_2023.csv"],
  ["../data/processed/documented_smoke_episodes_1950_2005.csv", "public/data/documented_smoke_episodes_1950_2005.csv"],
  ["../data/processed/historical_smoke_events_1950_2005.csv", "public/data/historical_smoke_events_1950_2005.csv"],
  ["../data/processed/historical_smoke_observations_1950_2005.csv", "public/data/historical_smoke_observations_1950_2005.csv"],
  ["../data/processed/historical_smoke_sources.csv", "public/data/historical_smoke_sources.csv"],
  ["../data/processed/historical_smoke_search_coverage_1950_2005.csv", "public/data/historical_smoke_search_coverage_1950_2005.csv"],
  ["../data/processed/noaa_storm_events_wildfire_candidates_1950_2005.csv", "public/data/noaa_storm_events_wildfire_candidates_1950_2005.csv"],
  ["../data/processed/mtbs_wildfires_annual.csv", "public/data/mtbs_wildfires_annual.csv"],
  ["../data/processed/canada_fire_annual.csv", "public/data/canada_fire_annual.csv"],
  ["../data/processed/stanford_annual_smoke_2006_2023.csv", "public/data/stanford_annual_smoke_2006_2023.csv"],
  ["../data/processed/stanford_daily_smoke_2006_2023.csv", "public/data/stanford_daily_smoke_2006_2023.csv"],
  ["../data/processed/operational_smoke_proxy_annual_2024_2026.csv", "public/data/operational_smoke_proxy_annual_2024_2026.csv"],
  ["../data/processed/operational_smoke_screen_annual_2006_2026.csv", "public/data/operational_smoke_screen_annual_2006_2026.csv"],
  ["../data/processed/operational_smoke_screen_daily_2006_2026.csv", "public/data/operational_smoke_screen_daily_2006_2026.csv"],
  ["../data/processed/operational_smoke_screen_same_cutoff_2006_2026.csv", "public/data/operational_smoke_screen_same_cutoff_2006_2026.csv"],
  ["../data/processed/operational_smoke_screen_monitor_coverage_2006_2026.csv", "public/data/operational_smoke_screen_monitor_coverage_2006_2026.csv"],
  ["../data/processed/operational_smoke_screen_audit_2006_2026.json", "public/data/operational_smoke_screen_audit_2006_2026.json"],
  ["../data/processed/zcta_smoke_exposure_2021.csv", "public/data/zcta_smoke_exposure_2021.csv"],
  ["../sources/manifest.json", "public/data/source_manifest.json"],
];

for (const [sourcePath, targetPath] of copies) {
  const source = resolve(siteRoot, sourcePath);
  const target = resolve(siteRoot, targetPath);
  await mkdir(dirname(target), { recursive: true });
  await copyFile(source, target);
}

console.log(`Synced ${copies.length} data files to site/public/data`);
