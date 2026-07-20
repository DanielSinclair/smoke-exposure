#!/usr/bin/env python3
"""Render publication-ready social graphics from the canonical dashboard contract."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from pipeline.settings import PROCESSED, ROOT


WIDTH = 2400
HEIGHT = 1350
OUTPUT = ROOT / "site" / "public" / "social"
BACKGROUND = "#F7F6F1"
INK = "#141413"
MUTED = "#65645F"
LIGHT = "#E2E1DB"
MID = "#A5A49E"
DARK = "#4A4946"
WHITE = "#FFFFFF"
ACCENT = "#1B365D"
GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
MONO = "/System/Library/Fonts/SFNSMono.ttf"


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(MONO if mono else GEORGIA_BOLD if bold else GEORGIA, size)


TITLE = font(72)
DISPLAY = font(104)
SUBHEAD = font(40, bold=True)
BODY = font(32)
SMALL = font(24)
LABEL = font(22, mono=True)
AXIS = font(19, mono=True)


def compact(value: float, digits: int = 1) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.{digits}f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.{digits}f}M"
    if value >= 1_000:
        return f"{value / 1_000:.{digits}f}K"
    return f"{value:,.0f}"


def wrap(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if draw.textbbox((0, 0), candidate, font=selected_font)[2] <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def text_block(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    selected_font: ImageFont.FreeTypeFont,
    width: int,
    *,
    fill: str = INK,
    spacing: int = 12,
) -> int:
    x, y = xy
    line_height = selected_font.size + spacing
    for line in wrap(draw, text, selected_font, width):
        draw.text((x, y), line, font=selected_font, fill=fill)
        y += line_height
    return y


def base_canvas(kicker: str, title: str) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((100, 78), kicker.upper(), font=LABEL, fill=MUTED)
    title_bottom = text_block(draw, (100, 132), title, TITLE, 2150, spacing=9)
    draw.line((100, title_bottom + 24, 2300, title_bottom + 24), fill=INK, width=3)
    return image, draw, title_bottom + 64


def footer(draw: ImageDraw.ImageDraw, source: str, status: str) -> None:
    draw.line((100, 1260, 2300, 1260), fill=INK, width=2)
    draw.text((100, 1284), source, font=SMALL, fill=MUTED)
    right = "smoke-exposure · Daniel Sinclair"
    right_width = draw.textbbox((0, 0), right, font=SMALL)[2]
    draw.text((2300 - right_width, 1284), right, font=SMALL, fill=MUTED)
    draw.text((100, 1320), status, font=AXIS, fill=MUTED)


def write_png(image: Image.Image, name: str, title: str, description: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    info = PngImagePlugin.PngInfo()
    info.add_text("Title", title)
    info.add_text("Description", description)
    info.add_text("Source", "https://github.com/DanielSinclair/smoke-exposure")
    info.add_text("Dimensions", f"{WIDTH}x{HEIGHT} (16:9)")
    image.save(OUTPUT / name, format="PNG", optimize=True, pnginfo=info)


def chart_frame(draw: ImageDraw.ImageDraw, left: int, top: int, right: int, bottom: int, maximum: float, ticks: Iterable[float]) -> None:
    for value in ticks:
        y = bottom - (value / maximum) * (bottom - top)
        draw.line((left, y, right, y), fill=LIGHT, width=2)
        label = compact(value, 0)
        label_width = draw.textbbox((0, 0), label, font=AXIS)[2]
        draw.text((left - label_width - 18, y - 12), label, font=AXIS, fill=MUTED)


def polyline(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], *, fill: str, width: int, dash: bool = False) -> None:
    if not dash:
        draw.line(points, fill=fill, width=width, joint="curve")
        return
    for start, end in zip(points, points[1:]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.hypot(dx, dy)
        if distance == 0:
            continue
        step = 24
        for offset in range(0, int(distance), step):
            if (offset // step) % 2:
                continue
            t1 = offset / distance
            t2 = min((offset + step * 0.58) / distance, 1)
            draw.line((start[0] + dx * t1, start[1] + dy * t1, start[0] + dx * t2, start[1] + dy * t2), fill=fill, width=width)


def render_smoke_trend(data: dict) -> None:
    rows = data["annual_smoke"]
    trend = data["smoke_trend"]
    image, draw, content_top = base_canvas("01 · Modeled U.S. exposure", "Wildfire smoke exposure rose sharply after 2016")
    draw.text((100, content_top + 32), f"{trend['recent_to_early_multiplier']:.1f}×", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 158), "higher average burden", SUBHEAD, 620, spacing=4)
    y = text_block(draw, (100, y + 18), f"{trend['recent_period']} compared with {trend['early_period']}.", BODY, 620, fill=MUTED)
    text_block(draw, (100, y + 32), f"The recent five-year average reached {compact(trend['recent_average_population_days'])} person-days, up from {compact(trend['early_average_population_days'])}.", BODY, 620, fill=INK)

    left, top, right, bottom = 920, content_top + 50, 2290, 1115
    maximum = 600_000_000
    chart_frame(draw, left, top, right, bottom, maximum, [0, 200_000_000, 400_000_000, 600_000_000])
    x = lambda year: left + (year - 2006) / (2023 - 2006) * (right - left)
    y_for = lambda value: bottom - value / maximum * (bottom - top)
    annual = [(x(row["year"]), y_for(row["population_days"])) for row in rows]
    rolling = [(x(row["year"]), y_for(row["value"])) for row in trend["rolling_mean_5yr"]]
    polyline(draw, annual, fill=INK, width=7)
    polyline(draw, rolling, fill=MUTED, width=4, dash=True)
    for row, point in zip(rows, annual):
        radius = 11 if row["year"] in (2020, 2023) else 6
        draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=BACKGROUND, outline=INK, width=5)
    for year in [2006, 2010, 2014, 2018, 2023]:
        label = str(year)
        label_width = draw.textbbox((0, 0), label, font=AXIS)[2]
        draw.text((x(year) - label_width / 2, bottom + 22), label, font=AXIS, fill=MUTED)
    for year in [2020, 2023]:
        row = next(item for item in rows if item["year"] == year)
        px, py = x(year), y_for(row["population_days"])
        label = f"{year}  {compact(row['population_days'])}"
        label_width = draw.textbbox((0, 0), label, font=SMALL)[2]
        draw.rectangle((px - label_width - 30, py - 57, px + 12, py - 14), fill=BACKGROUND)
        draw.text((px - label_width - 18, py - 52), label, font=SMALL, fill=INK)
    draw.line((1660, 1180, 1750, 1180), fill=INK, width=6)
    draw.text((1768, 1165), "annual estimate", font=SMALL, fill=MUTED)
    polyline(draw, [(2010, 1180), (2100, 1180)], fill=MUTED, width=4, dash=True)
    draw.text((2118, 1165), "5-year average", font=SMALL, fill=MUTED)
    footer(draw, "Stanford ECHO v2 beta · fixed July 1, 2020 population", "Comparable modeled years 2006–2023 · AQI-101-equivalent wildfire-smoke increment")
    write_png(image, "01-modeled-smoke-trend.png", "Wildfire smoke exposure rose sharply after 2016", "Annual modeled high-smoke person-days in the United States, 2006–2023.")


def history_level(days: int) -> int:
    if days == 0:
        return 0
    if days <= 3:
        return 1
    if days <= 7:
        return 2
    if days <= 14:
        return 3
    return 4


def dashed_rectangle(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, width: int = 3) -> None:
    left, top, right, bottom = box
    for start in range(left, right, 16):
        draw.line((start, top, min(start + 8, right), top), fill=fill, width=width)
        draw.line((start, bottom, min(start + 8, right), bottom), fill=fill, width=width)
    for start in range(top, bottom, 16):
        draw.line((left, start, left, min(start + 8, bottom)), fill=fill, width=width)
        draw.line((right, start, right, min(start + 8, bottom)), fill=fill, width=width)


def render_monthly_history(data: dict) -> None:
    rows = [
        row for row in data["smoke_history"]
        if any(
            month["events"]
            or month["status"] in ("modeled_comparable", "operational_proxy")
            for month in row["months"]
        )
    ]
    documentary_years = sum(
        any(month["events"] for month in row["months"]) and row["year"] < 2006
        for row in rows
    )
    image, draw, content_top = base_canvas("02 · Documented and national evidence", "Monthly U.S. smoke evidence")
    draw.text((100, content_top + 34), f"{len(rows)}", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 160), "years with recorded evidence", SUBHEAD, 620, spacing=4)
    y = text_block(draw, (100, y + 18), f"{documentary_years} pre-2006 years contain source-backed cases. 2006–2023 uses the comparable Stanford model; 2024–2026 is a separate recent screen.", BODY, 650, fill=MUTED)
    text_block(draw, (100, y + 36), "Only years with a documented case or national daily data appear. Unfilled documentary months mean unknown—not zero exposure.", BODY, 650, fill=INK)

    left, top = 1045, content_top + 44
    cell_w, cell_h, gap = 88, 24, 4
    colors = [WHITE, "#D9D8D2", "#AAA9A3", "#64635F", INK]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for index, month in enumerate(months):
        label_width = draw.textbbox((0, 0), month, font=AXIS)[2]
        draw.text((left + index * (cell_w + gap) + cell_w / 2 - label_width / 2, top - 42), month, font=AXIS, fill=MUTED)
    for row_index, row in enumerate(rows):
        row_y = top + row_index * (cell_h + gap)
        draw.text((left - 85, row_y + 4), str(row["year"]), font=AXIS, fill=INK if row["year"] in (2006, 2023, 2024, 2026) else MUTED)
        for month_index, month in enumerate(row["months"]):
            cell_x = left + month_index * (cell_w + gap)
            box = (cell_x, row_y, cell_x + cell_w, row_y + cell_h)
            if month["status"] == "not_yet_observed":
                draw.rectangle(box, fill=BACKGROUND, outline=LIGHT, width=2)
                draw.line((cell_x + 8, row_y + cell_h - 7, cell_x + cell_w - 8, row_y + 7), fill=LIGHT, width=2)
                continue
            if month["status"] == "no_comparable_daily_data":
                draw.rectangle(box, fill=BACKGROUND, outline=LIGHT, width=2)
                if month["events"]:
                    draw.rectangle(box, fill="#E5E1D8", outline=MUTED, width=2)
                    for offset in range(-cell_h, cell_w, 12):
                        draw.line(
                            (max(cell_x, cell_x + offset), max(row_y, row_y - offset),
                             min(cell_x + cell_w, cell_x + offset + cell_h), min(row_y + cell_h, row_y + cell_h)),
                            fill="#B7B1A6", width=2,
                        )
                    count = str(len(month["events"]))
                    count_box = draw.textbbox((0, 0), count, font=AXIS)
                    draw.rectangle((cell_x + 3, row_y + 2, cell_x + 9 + count_box[2], row_y + cell_h - 2), fill=BACKGROUND)
                    draw.text((cell_x + 6, row_y), count, font=AXIS, fill=INK)
                continue
            level = history_level(month["smoke_days"] or 0)
            draw.rectangle(box, fill=colors[level], outline=LIGHT if level == 0 else colors[level], width=2)
            if month["status"] == "operational_proxy":
                dashed_rectangle(draw, box, INK, 3)
        if row["year"] in (2005, 2023):
            divider_y = row_y + cell_h + 4
            draw.line((left - 85, divider_y, left + 12 * (cell_w + gap) - gap, divider_y), fill=INK, width=3)
    legend_y = 1000
    draw.text((100, legend_y), "national high-smoke days", font=SMALL, fill=MUTED)
    labels = ["0", "1–3", "4–7", "8–14", "15+"]
    for index, (color, label) in enumerate(zip(colors, labels)):
        x = 380 + index * 135
        draw.rectangle((x, legend_y - 2, x + 42, legend_y + 28), fill=color, outline=LIGHT, width=2)
        draw.text((x + 52, legend_y - 2), label, font=SMALL, fill=MUTED)
    footer(draw, "27 documentary sources; Stanford ECHO; EPA AQS/AirNow + NOAA HMS", "Patterned cells: documented cases · solid: comparable model · dashed: recent screen")
    write_png(image, "02-monthly-smoke-history.png", "Monthly U.S. smoke evidence", "Documentary episodes and national smoke-exposure data for the years in which evidence is available, 1950–2026.")


def render_worst_days(data: dict) -> None:
    rows = data["extremes"]["top_days"]
    image, draw, content_top = base_canvas("03 · Largest modeled daily reach", "The worst smoke days reached tens of millions")
    worst = rows[0]
    draw.text((100, content_top + 30), compact(worst["population_exposed"]), font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 155), "people on June 29, 2023", SUBHEAD, 650, spacing=4)
    y = text_block(draw, (100, y + 18), f"{worst['share_of_population']:.1f}% of the fixed U.S. population encountered an unhealthy wildfire-smoke increment that day.", BODY, 650, fill=MUTED)
    count_2023 = sum(1 for row in rows if row["date"].startswith("2023"))
    text_block(draw, (100, y + 36), f"{count_2023} of the ten largest modeled days occurred during the 2023 smoke season.", BODY, 650, fill=INK)

    left, top, right = 980, content_top + 38, 2290
    bar_height, row_gap = 48, 26
    maximum = max(row["population_exposed"] for row in rows)
    for index, row in enumerate(rows):
        y_row = top + index * (bar_height + row_gap)
        date = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %-d, %Y")
        draw.text((left, y_row + 8), f"{index + 1}", font=AXIS, fill=MUTED)
        draw.text((left + 50, y_row + 8), date, font=SMALL, fill=INK)
        bar_left = left + 330
        draw.rectangle((bar_left, y_row, right, y_row + bar_height), fill=LIGHT)
        bar_right = bar_left + row["population_exposed"] / maximum * (right - bar_left)
        draw.rectangle((bar_left, y_row, bar_right, y_row + bar_height), fill=INK if index == 0 else DARK)
        value = f"{compact(row['population_exposed'])} · {row['share_of_population']:.1f}%"
        value_width = draw.textbbox((0, 0), value, font=SMALL)[2]
        draw.text((right - value_width, y_row + 7), value, font=SMALL, fill=WHITE if bar_right > right - value_width - 20 else INK)
    footer(draw, "Stanford ECHO v2 beta · modeled county-day wildfire-smoke PM₂.₅", "Fixed 2020 population · daily AQI-101-equivalent smoke increment · 2006–2023")
    write_png(image, "03-worst-smoke-days.png", "The worst smoke days reached tens of millions", "The ten modeled days with the broadest U.S. high-smoke exposure, 2006–2023.")


def render_burned_area(data: dict) -> None:
    canada = [row for row in data["annual_canada_fire"] if row["year"] <= 2025 and not row.get("provisional")]
    united_states = [row for row in data["annual_fire"] if row["year"] <= 2024 and not row.get("provisional")]
    trends = data["fire_trends"]
    image, draw, content_top = base_canvas("04 · Complete annual fire records", "North American fire seasons now burn more land")
    draw.text((100, content_top + 20), "+99%", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 145), "Canada", SUBHEAD, 620, spacing=4)
    y = text_block(draw, (100, y + 10), f"Recent decade vs {trends['canada']['first_period']}", BODY, 620, fill=MUTED)
    draw.text((100, y + 42), "+239%", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, y + 166), "United States", SUBHEAD, 620, spacing=4)
    text_block(draw, (100, y + 10), f"Recent decade vs {trends['united_states']['first_period']}", BODY, 620, fill=MUTED)

    left, top, right, bottom = 920, content_top + 30, 2290, 1115
    maximum = 40_000_000
    chart_frame(draw, left, top, right, bottom, maximum, [0, 10_000_000, 20_000_000, 30_000_000, 40_000_000])
    x = lambda year: left + (year - 1972) / (2025 - 1972) * (right - left)
    y_for = lambda value: bottom - value / maximum * (bottom - top)
    canada_points = [(x(row["year"]), y_for(row["acres_burned"])) for row in canada]
    us_points = [(x(row["year"]), y_for(row["acres_burned"])) for row in united_states]
    polyline(draw, canada_points, fill=ACCENT, width=7)
    polyline(draw, us_points, fill=INK, width=5, dash=True)
    for point in canada_points:
        draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill=ACCENT)
    for year in [1972, 1980, 1990, 2000, 2010, 2020, 2025]:
        label_width = draw.textbbox((0, 0), str(year), font=AXIS)[2]
        draw.text((x(year) - label_width / 2, bottom + 22), str(year), font=AXIS, fill=MUTED)
    peak = max(canada, key=lambda row: row["acres_burned"])
    px, py = x(peak["year"]), y_for(peak["acres_burned"])
    draw.text((px - 190, py - 52), f"Canada {peak['year']} · {compact(peak['acres_burned'])}", font=SMALL, fill=ACCENT)
    draw.line((1470, 1180, 1560, 1180), fill=ACCENT, width=7)
    draw.text((1578, 1165), "Canada NBAC", font=SMALL, fill=MUTED)
    polyline(draw, [(1880, 1180), (1970, 1180)], fill=INK, width=5, dash=True)
    draw.text((1988, 1165), "U.S. MTBS large fires", font=SMALL, fill=MUTED)
    footer(draw, "NRCan NBAC 1972–2025; U.S. MTBS 1984–2024", "Complete annual acres · current 2026 YTD totals excluded from trendlines")
    write_png(image, "04-burned-area-trendlines.png", "North American fire seasons now burn more land", "Complete annual burned-area trendlines for Canada and mapped U.S. large fires.")


def render_recent_comparison(data: dict) -> None:
    rows = [
        row for row in data["smoke_same_cutoff"]
        if row["series_kind"] == "operational_proxy"
    ]
    image, draw, content_top = base_canvas("05 · Same-window observed screen", "2026 ranks second through July 18")
    current = next(row for row in rows if row["year"] == 2026)
    burden_order = sorted(rows, key=lambda row: row["population_days"], reverse=True)
    peak_order = sorted(rows, key=lambda row: row["peak_population"], reverse=True)
    burden_rank = next(index + 1 for index, row in enumerate(burden_order) if row["year"] == 2026)
    peak_rank = next(index + 1 for index, row in enumerate(peak_order) if row["year"] == 2026)
    draw.text((100, content_top + 26), compact(current["population_days"]), font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 152), "indicative population-days", SUBHEAD, 660, spacing=4)
    y = text_block(draw, (100, y + 18), f"{burden_rank}nd of {len(rows)} years in the Jan 1–Jul 18 observed screen.", BODY, 650, fill=MUTED)
    text_block(draw, (100, y + 38), f"Peak daily reach was {compact(current['peak_population'])}, also {peak_rank}nd. The 2023 screen remains higher on both measures.", BODY, 650, fill=INK)

    left, right = 940, 2290
    chart_width = right - left
    bar_gap = 10
    bar_width = (chart_width - bar_gap * (len(rows) - 1)) / len(rows)
    panels = [
        ("Indicative population-days", "sum of qualifying county population", "population_days", compact),
        ("Peak daily reach", "largest qualifying county footprint", "peak_population", compact),
    ]
    for panel_index, (title, subtitle, key, formatter) in enumerate(panels):
        panel_top = content_top + 28 + panel_index * 465
        chart_top = panel_top + 104
        chart_bottom = panel_top + 380
        maximum = max(row[key] for row in rows)
        draw.text((left, panel_top), title, font=SUBHEAD, fill=INK)
        draw.text((left, panel_top + 52), subtitle, font=SMALL, fill=MUTED)
        draw.line((left, chart_bottom, right, chart_bottom), fill=LIGHT, width=2)
        for index, row in enumerate(rows):
            x0 = left + index * (bar_width + bar_gap)
            height = row[key] / maximum * (chart_bottom - chart_top)
            fill = INK if row["year"] == 2026 else MID
            draw.rectangle((x0, chart_bottom - height, x0 + bar_width, chart_bottom), fill=fill)
            if row["year"] in (2006, 2010, 2015, 2020, 2023, 2026):
                label = str(row["year"])[2:]
                label_width = draw.textbbox((0, 0), label, font=AXIS)[2]
                draw.text((x0 + bar_width / 2 - label_width / 2, chart_bottom + 12), label, font=AXIS, fill=INK if row["year"] == 2026 else MUTED)
            if row["year"] in (2023, 2026):
                value = formatter(row[key])
                value_width = draw.textbbox((0, 0), value, font=SMALL)[2]
                draw.text((x0 + bar_width / 2 - value_width / 2, chart_bottom - height - 32), value, font=SMALL, fill=INK)
    footer(draw, "EPA AQS total PM₂.₅ + NOAA HMS smoke polygons; AirNow supplement in 2026", "Every year Jan 1–Jul 18 · observed screen with coverage sensitivity · not Stanford-equivalent")
    write_png(image, "05-recent-smoke-comparison.png", "2026 ranks second through July 18", "Same-window monitor-and-satellite smoke comparison for every year from 2006 through 2026.")


def render_seasonality(data: dict) -> None:
    seasonality = data["seasonality"]
    early = seasonality["era_1"]
    recent = seasonality["era_2"]
    notable = {row["year"]: row for row in seasonality["notable_years"]}
    image, draw, content_top = base_canvas("06 · Modeled seasonal concentration", "Smoke exposure shifted later in the season")
    draw.text((100, content_top + 26), f"{notable[2023]['share_percent']:.1f}%", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 152), "of 2023 person-days occurred in June", SUBHEAD, 660, spacing=4)
    y = text_block(draw, (100, y + 20), f"September carried {recent['monthly_share'][8]:.1f}% of the {recent['period']} burden, compared with {early['monthly_share'][8]:.1f}% in {early['period']}.", BODY, 670, fill=MUTED)
    text_block(draw, (100, y + 40), f"Other concentrated seasons: September 2020 accounted for {notable[2020]['share_percent']:.1f}% of that year; November 2018 accounted for {notable[2018]['share_percent']:.1f}%.", BODY, 670, fill=INK)

    months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    shades = ["#F7F6F1", "#E2E1DB", "#C1C0BA", "#85847E", INK]
    left, right = 930, 2290
    cell_gap = 12
    cell_width = (right - left - cell_gap * 11) / 12
    for index, month in enumerate(months):
        width = draw.textbbox((0, 0), month, font=AXIS)[2]
        draw.text((left + index * (cell_width + cell_gap) + cell_width / 2 - width / 2, content_top + 38), month, font=AXIS, fill=MUTED)
    for row_index, era in enumerate((early, recent)):
        top = content_top + 92 + row_index * 250
        draw.text((left, top), era["period"], font=SUBHEAD, fill=INK)
        cell_top = top + 68
        for index, share in enumerate(era["monthly_share"]):
            if share == 0:
                level = 0
            elif share < 2:
                level = 1
            elif share < 10:
                level = 2
            elif share < 20:
                level = 3
            else:
                level = 4
            x = left + index * (cell_width + cell_gap)
            draw.rectangle((x, cell_top, x + cell_width, cell_top + 96), fill=shades[level], outline=LIGHT, width=2)
            label = f"{share:.1f}"
            label_width = draw.textbbox((0, 0), label, font=AXIS)[2]
            draw.text((x + cell_width / 2 - label_width / 2, cell_top + 108), label, font=AXIS, fill=INK if level < 4 else MUTED)
    draw.text((left, content_top + 620), "Share of each era's modeled population-days by calendar month", font=SMALL, fill=MUTED)
    for index, (year, label) in enumerate(((2018, "November"), (2020, "September"), (2023, "June"))):
        top = content_top + 700 + index * 112
        value = notable[year]["share_percent"]
        draw.text((left, top), str(year), font=SMALL, fill=MUTED)
        draw.text((left + 118, top), label, font=SMALL, fill=INK)
        draw.rectangle((left + 360, top + 4, right, top + 31), fill=LIGHT)
        draw.rectangle((left + 360, top + 4, left + 360 + (right - left - 360) * value / 100, top + 31), fill=INK)
        draw.text((right - 92, top + 44), f"{value:.1f}%", font=AXIS, fill=MUTED)
    footer(draw, "Stanford ECHO v2 beta · modeled county-day wildfire-smoke PM₂.₅", "Monthly shares of annual population-days · fixed July 1, 2020 population · 2006–2023")
    write_png(image, "06-seasonality-shift.png", "Smoke exposure shifted later in the season", "Modeled wildfire-smoke population-days by calendar month and notable concentrated seasons.")


def render_regional_concentration(data: dict) -> None:
    shift = data["regional_shift"]["top5_2023"]
    rows = sorted(
        (row for row in data["smoke_region_context"] if row["year"] == 2023),
        key=lambda row: row["high_smoke_population_days"],
        reverse=True,
    )[:5]
    image, draw, content_top = base_canvas("07 · 2023 modeled regional burden", "Five states carried half of the national burden")
    draw.text((100, content_top + 26), f"{shift['share_percent']}%", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 152), "of 2023 population-days", SUBHEAD, 650, spacing=4)
    y = text_block(draw, (100, y + 20), "New York, Pennsylvania, Ohio, Michigan and New Jersey formed the highest-burden group.", BODY, 660, fill=MUTED)
    text_block(draw, (100, y + 42), f"New York alone recorded {compact(rows[0]['high_smoke_population_days'])} modeled high-smoke population-days.", BODY, 660, fill=INK)

    left, right, top = 930, 2290, content_top + 45
    maximum = rows[0]["high_smoke_population_days"]
    for index, row in enumerate(rows):
        y_row = top + index * 168
        draw.text((left, y_row), f"{index + 1}", font=AXIS, fill=MUTED)
        draw.text((left + 52, y_row - 7), row["state"], font=SUBHEAD, fill=INK)
        bar_top = y_row + 54
        draw.rectangle((left + 52, bar_top, right, bar_top + 50), fill=LIGHT)
        width = (right - left - 52) * row["high_smoke_population_days"] / maximum
        draw.rectangle((left + 52, bar_top, left + 52 + width, bar_top + 50), fill=INK if index == 0 else DARK)
        value = f"{compact(row['high_smoke_population_days'])} population-days"
        value_width = draw.textbbox((0, 0), value, font=SMALL)[2]
        draw.text((right - value_width, bar_top + 62), value, font=SMALL, fill=MUTED)
    footer(draw, "Stanford ECHO v2 beta · state aggregation of modeled county-day exposure", "2023 high-smoke population-days · state totals overlap people across qualifying days")
    write_png(image, "07-regional-concentration.png", "Five states carried half of the national burden", "The five highest-burden states accounted for 52 percent of modeled 2023 U.S. wildfire-smoke population-days.")


def render_historical_review_coverage(data: dict) -> None:
    rows = [row for row in data["smoke_history"] if row["year"] <= 2005]
    episode_counts: dict[int, int] = {}
    for event in data["documented_smoke_episodes"]:
        year = int(event["start_date"][:4])
        episode_counts[year] = episode_counts.get(year, 0) + 1
    totals = []
    for row in rows:
        reviewed = sum(
            month.get("review_status") in ("searched_no_qualifying_case_found", "reviewed_with_evidence")
            for month in row["months"]
        )
        events = episode_counts.get(row["year"], 0)
        totals.append({"year": row["year"], "reviewed": reviewed, "events": events})
    reviewed_total = sum(row["reviewed"] for row in totals)
    month_total = len(rows) * 12
    event_total = sum(row["events"] for row in totals)
    image, draw, content_top = base_canvas("08 · Historical evidence coverage", "Most pre-2006 months remain unreviewed")
    draw.text((100, content_top + 26), f"{month_total - reviewed_total}", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 152), f"of {month_total} months remain unreviewed", SUBHEAD, 680, spacing=4)
    y = text_block(draw, (100, y + 20), f"The catalog currently accepts {event_total} documentary smoke episodes across {sum(row['events'] > 0 for row in totals)} pre-2006 years.", BODY, 670, fill=MUTED)
    text_block(draw, (100, y + 42), "Systematic month-by-month screening begins in 1996. Earlier case years are evidence of episodes, not complete annual searches.", BODY, 670, fill=INK)

    left, right = 930, 2290
    gap = 3
    cell_width = (right - left - gap * (len(totals) - 1)) / len(totals)
    ticks = {1950, 1960, 1970, 1980, 1990, 2000, 2005}
    for row_index, (label, key, maximum, shades) in enumerate((
        ("Months systematically reviewed", "reviewed", 12, ["#F7F6F1", "#D8D7D1", "#AAA9A3", "#686762", INK]),
        ("Accepted documentary episodes", "events", max(row["events"] for row in totals), ["#F7F6F1", "#D8D7D1", "#AAA9A3", "#686762", INK]),
    )):
        top = content_top + 90 + row_index * 320
        draw.text((left, top), label, font=SUBHEAD, fill=INK)
        cell_top = top + 76
        for index, row in enumerate(totals):
            value = row[key]
            level = 0 if value == 0 else min(4, max(1, math.ceil(value / maximum * 4)))
            x = left + index * (cell_width + gap)
            draw.rectangle((x, cell_top, x + cell_width, cell_top + 96), fill=shades[level], outline=LIGHT, width=1)
            if row["year"] in ticks:
                year = str(row["year"])
                label_width = draw.textbbox((0, 0), year, font=AXIS)[2]
                draw.text((x + cell_width / 2 - label_width / 2, cell_top + 118), year, font=AXIS, fill=MUTED)
        if key == "reviewed":
            draw.text((left, cell_top + 176), f"{reviewed_total} months reviewed · {month_total - reviewed_total} unknown", font=SMALL, fill=MUTED)
        else:
            draw.text((left, cell_top + 176), f"{event_total} accepted episodes · absence of a cell does not mean clean air", font=SMALL, fill=MUTED)
    footer(draw, "Historical smoke-evidence catalog · NOAA Storm Events candidate screen + cited episode sources", "1950–2005 documentary evidence · non-comparable with the 2006–2023 modeled series")
    write_png(image, "08-historical-review-coverage.png", "Most pre-2006 months remain unreviewed", "Historical source-review coverage and accepted documentary wildfire-smoke episodes from 1950 through 2005.")


def quantile_thresholds(values: list[int], bands: int = 5) -> list[float]:
    ordered = sorted(value for value in values if value > 0)
    if not ordered:
        return []
    thresholds = []
    for index in range(1, bands):
        position = (len(ordered) - 1) * index / bands
        lower = math.floor(position)
        upper = math.ceil(position)
        thresholds.append(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))
    return thresholds


def quantile_level(value: int | None, thresholds: list[float]) -> int:
    if value is None:
        return -1
    if value <= 0:
        return 0
    return min(5, 1 + sum(value > threshold for threshold in thresholds))


def render_fire_record_coverage(data: dict) -> None:
    rows = data["fire_incident_catalog"]
    years = list(range(1950, 2027))
    geographies = ("United States", "Canada")
    by_key = {(row["geography"], row["year"]): row for row in rows}
    thresholds = {
        geography: quantile_thresholds([row["record_count"] or 0 for row in rows if row["geography"] == geography])
        for geography in geographies
    }
    missing_us = sum(by_key[("United States", year)]["record_count"] is None for year in years)
    image, draw, content_top = base_canvas("09 · Source-covered fire records", "National fire catalogs do not cover every era equally")
    draw.text((100, content_top + 26), f"{missing_us}", font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 152), "U.S. years lack a national incident catalog", SUBHEAD, 680, spacing=4)
    y = text_block(draw, (100, y + 20), "Canadian NFDB coverage begins in 1950. U.S. coverage begins with MTBS large fires in 1984 and broadens with FPA FOD in 1992.", BODY, 680, fill=MUTED)
    text_block(draw, (100, y + 42), "Each country uses its own count quintiles. Shade shows archive density—not directly comparable fire incidence.", BODY, 680, fill=INK)

    left, right = 930, 2290
    gap = 2
    cell_width = (right - left - gap * (len(years) - 1)) / len(years)
    shades = ["#F4F3EE", "#ECEAE4", "#CDC6BE", "#9D9389", "#655D56", "#211F1D"]
    ticks = {1950, 1970, 1990, 2006, 2020, 2026}
    for index, year in enumerate(years):
        if year in ticks:
            x = left + index * (cell_width + gap)
            label = str(year)
            label_width = draw.textbbox((0, 0), label, font=AXIS)[2]
            draw.text((x + cell_width / 2 - label_width / 2, content_top + 55), label, font=AXIS, fill=MUTED)
    for row_index, geography in enumerate(geographies):
        top = content_top + 130 + row_index * 260
        draw.text((left, top), geography, font=SUBHEAD, fill=INK)
        cell_top = top + 72
        for index, year in enumerate(years):
            value = by_key[(geography, year)]["record_count"]
            level = quantile_level(value, thresholds[geography])
            x = left + index * (cell_width + gap)
            box = (x, cell_top, x + cell_width, cell_top + 100)
            if level < 0:
                draw.rectangle(box, fill=BACKGROUND, outline=LIGHT, width=1)
                draw.line((x + 2, cell_top + 98, x + cell_width - 2, cell_top + 2), fill=LIGHT, width=2)
            else:
                draw.rectangle(box, fill=shades[level], outline=LIGHT, width=1)
    legend_top = content_top + 730
    draw.text((left, legend_top), "fewer records", font=SMALL, fill=MUTED)
    for index, shade in enumerate(shades[1:]):
        x = left + 190 + index * 75
        draw.rectangle((x, legend_top, x + 54, legend_top + 38), fill=shade, outline=LIGHT, width=1)
    draw.text((left + 585, legend_top), "more records", font=SMALL, fill=MUTED)
    draw.rectangle((left, legend_top + 92, left + 54, legend_top + 130), fill=BACKGROUND, outline=LIGHT, width=1)
    draw.line((left + 4, legend_top + 126, left + 50, legend_top + 96), fill=LIGHT, width=2)
    draw.text((left + 74, legend_top + 95), "no national catalog", font=SMALL, fill=MUTED)
    footer(draw, "NRCan NFDB; U.S. MTBS, FPA FOD and NIFC InFORM", "1950–2026 archive coverage · independently scaled record-count quintiles · exact counts in project data")
    write_png(image, "09-fire-record-coverage.png", "National fire catalogs do not cover every era equally", "Annual source-covered U.S. and Canadian fire-record density from 1950 through 2026.")


def render_current_fire_activity(data: dict) -> None:
    rows = {row["geography"]: row for row in data["current_fire_activity"]}
    united_states = rows["United States"]
    canada = rows["Canada"]
    combined = united_states["burned_area_acres"] + canada["burned_area_acres"]
    image, draw, content_top = base_canvas("10 · Preliminary 2026 fire activity", "More than 11 million acres had burned by July 18")
    draw.text((100, content_top + 26), compact(combined), font=DISPLAY, fill=INK)
    y = text_block(draw, (100, content_top + 152), "combined reported acres", SUBHEAD, 650, spacing=4)
    y = text_block(draw, (100, y + 20), f"Canada reported {compact(canada['burned_area_acres'])} acres across {canada['fire_count']:,} fires; the United States reported {compact(united_states['burned_area_acres'])} acres across {united_states['fire_count']:,} fires.", BODY, 680, fill=MUTED)
    text_block(draw, (100, y + 42), "These are preliminary year-to-date activity totals, not complete annual trend points and not smoke-exposure estimates.", BODY, 680, fill=INK)

    chart_rows = (("Canada", canada, ACCENT), ("United States", united_states, INK))
    left, right = 930, 2290
    maximum = max(row[1]["burned_area_acres"] for row in chart_rows)
    for index, (label, row, color) in enumerate(chart_rows):
        top = content_top + 100 + index * 300
        draw.text((left, top), label, font=SUBHEAD, fill=INK)
        acres = f"{compact(row['burned_area_acres'])} acres"
        acres_width = draw.textbbox((0, 0), acres, font=SUBHEAD)[2]
        draw.text((right - acres_width, top), acres, font=SUBHEAD, fill=color)
        bar_top = top + 90
        draw.rectangle((left, bar_top, right, bar_top + 92), fill=LIGHT)
        bar_width = (right - left) * row["burned_area_acres"] / maximum
        draw.rectangle((left, bar_top, left + bar_width, bar_top + 92), fill=color)
        draw.text((left, bar_top + 118), f"{row['fire_count']:,} reported fires", font=SMALL, fill=MUTED)
        draw.text((right - 280, bar_top + 118), "through Jul 18", font=SMALL, fill=MUTED)
    footer(draw, "NIFC IMSR and NRCan CWFIF · same July 18, 2026 cutoff", "Year-to-date and revisionable · country reporting systems differ · excluded from complete annual trendlines")
    write_png(image, "10-2026-fire-activity.png", "More than 11 million acres had burned by July 18", "Preliminary 2026 year-to-date fire counts and acres burned in the United States and Canada.")


def main() -> None:
    data = json.loads((PROCESSED / "dashboard.json").read_text())
    render_smoke_trend(data)
    render_monthly_history(data)
    render_worst_days(data)
    render_burned_area(data)
    render_recent_comparison(data)
    render_seasonality(data)
    render_regional_concentration(data)
    render_historical_review_coverage(data)
    render_fire_record_coverage(data)
    render_current_fire_activity(data)
    print(f"rendered 10 social graphics to {OUTPUT}")


if __name__ == "__main__":
    main()
