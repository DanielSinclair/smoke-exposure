# USA Today wildfire article: sources and preserved data

Retrieved July 18, 2026.

## Article

- USA Today, “We charted every wildfire since 1984. There's been a drastic increase” (July 16, 2026; updated July 17): https://www.usatoday.com/story/graphics/2026/07/16/wildfires-data-damage-historical-graphs/90861203007/

## Controlling fire dataset

- Monitoring Trends in Burn Severity (MTBS): https://www.mtbs.gov/
- Official direct-download portal: https://burnseverity.cr.usgs.gov/direct-download
- USDA Forest Service national download catalog: https://data.fs.usda.gov/geodata/edw/datasets.php?xmlKeyword=monitoring+trends+in+burn+severity
- Current MTBS Fire Occurrence Points shapefile, preserved at `../mtbs/S_USA.MTBS_FIRE_OCCURRENCE_PT.zip`.
- The archive's files are dated June 28, 2026. It contains 30,606 MTBS fire records and includes wildfire, prescribed fire, wildland-fire-use, and other fire types. Filter `FIRE_TYPE` explicitly before reproducing a wildfire-only chart.

MTBS consistently maps large U.S. fires from 1984 onward: generally at least 1,000 acres in the western U.S. and 500 acres in the eastern U.S. It includes Alaska, Hawaii, and Puerto Rico as well as CONUS. It contains burned-area and fire-severity information, not PM2.5, AQI, downwind exposure, or Canadian fire records.

## Article chart data

- Event timeline graphic: https://infogram.com/9181b19c-b3b6-456f-b658-b6a1cbb3b962
- Annual acreage graphic: https://infogram.com/0b2b39f6-0fa4-4f60-b9c2-2c1a87399bad
- Seasonal comparison graphic: https://infogram.com/92e96323-7a5e-4442-bcf0-364b63a2e3a7
- `annual_acres_1984_2024.csv` preserves the values embedded in the annual graphic.
- `seasonal_average_acres.csv` preserves the values shown in the seasonal graphic.

The article-derived annual values are not identical to a fresh aggregation of the June 2026 MTBS point archive. MTBS is revised quarterly, and the current archive includes partially mapped recent fire seasons. Treat the CSVs as a preserved snapshot of USA Today's analysis and the shapefile as the current official source, not as interchangeable vintages.

## Other sources cited by the article

- NOAA national temperature series used for the statement about 2026 warmth: https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/national/time-series/110/tavg/6/6/1895-2026
- Feng et al. (2025), “Large role of anthropogenic climate change in driving smoke concentrations across the western United States from 1992 to 2020”: https://doi.org/10.1073/pnas.2421903122
- Public model outputs for that paper, including GEOS-Chem control/background/natural-climate simulations for 1997–2020: https://doi.org/10.7910/DVN/QPFDSI
- U.S. Forest Service fire-sustainability report: https://www.fs.usda.gov/sites/default/files/fs_media/fs_document/sustainability-wildlandfire-508.pdf

The Feng et al. archive is scientifically relevant to smoke but is a separate western-U.S. modeled series, not the MTBS article data and not a national daily AQI product.
