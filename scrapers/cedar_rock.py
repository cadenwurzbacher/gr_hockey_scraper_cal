"""Cedar Rock Sportsplex scraper.

Schedule is in a view-only Google Sheet with multiple month tabs (grid layout):
- Row 0: month/year (e.g. "February 2026", "March", or "July 7, 2025 - August 3, 2025")
- Row 1: Column headers (Stick & Puck 12U, Stick & Puck 13+, etc.)
- Rows 6+: Date/Time/Cost blocks with events in columns

Uses current and future month sheets only. Past sheets often have year in name; current may not.
"""

import csv
import io
import re
from datetime import datetime

import requests

import os
from config import VENUES, CEDAR_ROCK_SHEET_URL, CEDAR_ROCK_GIDS, GOOGLE_SHEETS_API_KEY
from scrapers.base import Event, EASTERN_TZ

VENUE_ID = "cedar_rock"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]

DATE_RE = re.compile(r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\w*\s+(\d{1,2})/(\d{1,2})")
TIME_RE = re.compile(r"(\d{1,2}):?(\d{2})?\s*(AM|PM)?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(AM|PM)?", re.I)
MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _get_sheet_id(url: str) -> str | None:
    """Extract spreadsheet ID from URL."""
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    return m.group(1) if m else None


def _parse_year_month_from_cell(cell: str, now: datetime) -> tuple[int, int] | None:
    """Extract year and month from row 0 cell. Returns None if past or unparseable.

    Handles:
    - "February 2026" -> (2026, 2)
    - "March" (no year) -> (current_year, 3)
    - "July 7, 2025 - August 3, 2025" -> (2025, 7) from first date
    """
    cell = cell.strip()
    if not cell:
        return None

    # "Month YYYY"
    m = re.search(r"(\w+)\s+(\d{4})", cell)
    if m:
        month = MONTH_NAMES.get(m.group(1).lower())
        if month:
            return int(m.group(2)), month

    # "Month" only (current sheet, no year)
    for name, num in MONTH_NAMES.items():
        if re.match(rf"^{name}\s*$", cell, re.I):
            return now.year, num

    # "Month D, YYYY - ..." date range
    m = re.search(r"(\w+)\s+\d{1,2},\s*(\d{4})", cell)
    if m:
        month = MONTH_NAMES.get(m.group(1).lower())
        if month:
            return int(m.group(2)), month

    return None


def _parse_time_range(text: str, year: int, month: int, day: int) -> tuple[datetime, datetime] | None:
    """Parse '1:30-2:50 PM' or '12:00-1:30 PM (12U) $5' into start, end. Returns None if 12U only."""
    if re.search(r"\(12u\)", text, re.I) and not re.search(r"\(13\+\)|\(18\+\)", text, re.I):
        return None
    m = TIME_RE.search(text)
    if not m:
        return None
    sh, sm, samp, eh, em, eamp = m.groups()
    sh, sm = int(sh), int(sm or 0)
    eh, em = int(eh), int(em or 0)
    if not samp and eamp:
        samp = eamp
    if samp and samp.upper() == "PM" and sh != 12:
        sh += 12
    elif samp and samp.upper() == "AM" and sh == 12:
        sh = 0
    if eamp and eamp.upper() == "PM" and eh != 12:
        eh += 12
    elif eamp and eamp.upper() == "AM" and eh == 12:
        eh = 0
    start = datetime(year, month, day, sh, sm, tzinfo=EASTERN_TZ)
    end = datetime(year, month, day, eh, em, tzinfo=EASTERN_TZ)
    return start, end


def _parse_date_cell(text: str, year: int, month: int) -> int | None:
    """Parse 'Friday 2/13' -> day 13 (from M/D, second number is day)."""
    m = DATE_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(2))
    except (IndexError, ValueError):
        return None


def _scrape_one_sheet(
    sheet_id: str, gid: str | None, year: int, month: int, today: datetime.date, rows: list[list] | None = None
) -> list[Event]:
    """Scrape one sheet tab. Returns events for that month. Pass rows to avoid re-fetch."""
    if rows is None:
        url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            if gid is None
            else f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        )
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        rows = list(csv.reader(io.StringIO(resp.text)))
    if len(rows) < 7:
        return []

    # Check if this month is current or future
    first_of_month = datetime(year, month, 1).date()
    if first_of_month < today.replace(day=1):  # Same-month comparison: include current month
        if year < today.year or (year == today.year and month < today.month):
            return []  # Past month, skip

    events = []
    headers_row = rows[1]
    target_cols = []
    for i, cell in enumerate(headers_row):
        c = cell.strip().lower()
        if "stick" in c and "puck" in c:
            if "12u" in c or "12 u" in c:
                continue
            if "13+" in c or "13 +" in c or "18+" in c or "18 +" in c:
                target_cols.append((i, cell.strip()))
        if "open hockey" in c:
            target_cols.append((i, cell.strip()))

    for i in range(6, len(rows) - 1):
        for col_idx, col_title in target_cols:
            if col_idx >= len(rows[i]) or col_idx >= len(rows[i + 1]):
                continue
            date_cell = rows[i][col_idx].strip()
            time_cell = rows[i + 1][col_idx].strip()

            day = _parse_date_cell(date_cell, year, month)
            if day is None:
                continue

            try:
                event_date = datetime(year, month, day).date()
            except ValueError:
                continue
            if event_date < today:
                continue

            parsed = _parse_time_range(time_cell, year, month, day)
            if not parsed and i + 2 < len(rows) and col_idx < len(rows[i + 2]):
                cost_cell = rows[i + 2][col_idx]
                if "(13+)" in cost_cell or "(18+)" in cost_cell:
                    parsed = _parse_time_range(cost_cell, year, month, day)
            if not parsed:
                continue

            start, end = parsed
            events.append(
                Event(
                    venue=VENUE_NAME,
                    title=col_title,
                    start=start,
                    end=end,
                    url=CEDAR_ROCK_SHEET_URL,
                    source_id=f"cedarrock-{start.strftime('%Y%m%d')}-{col_title[:20]}",
                    location=ADDRESS,
                )
            )

    return events


def _discover_gids(sheet_id: str) -> list[str]:
    """Use Sheets API to get all sheet gids. Returns empty if no API key."""
    api_key = GOOGLE_SHEETS_API_KEY or os.environ.get("GOOGLE_SHEETS_API_KEY")
    if not api_key:
        return []
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?key={api_key}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        now = datetime.now(EASTERN_TZ)
        gids = []
        for sheet in data.get("sheets", []):
            props = sheet.get("properties", {})
            gid = str(props.get("sheetId", ""))
            title = (props.get("title") or "").strip()
            if not title or not gid:
                continue
            # Parse title: "March", "March 2026", "February 2026"
            parsed = _parse_year_month_from_cell(title, now)
            if parsed:
                year, month = parsed
                if year < now.year or (year == now.year and month < now.month):
                    continue
                gids.append(gid)
            else:
                gids.append(gid)  # Include if we can't parse (might be current)
        return gids
    except Exception:
        return []


def scrape() -> list[Event]:
    """Scrape Cedar Rock from all current and future month sheets."""
    if not CEDAR_ROCK_SHEET_URL:
        return []

    sheet_id = _get_sheet_id(CEDAR_ROCK_SHEET_URL)
    if not sheet_id:
        return []

    now = datetime.now(EASTERN_TZ)
    today = now.date()
    all_events = []

    # First: export without gid = current month tab (per Google Sheets default)
    gids_to_try = [None]  # None = no gid, use default/current tab
    gids_to_try.extend(_discover_gids(sheet_id) or CEDAR_ROCK_GIDS)

    for gid in gids_to_try:
        try:
            if gid is None:
                url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            else:
                url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            resp.raise_for_status()
            rows = list(csv.reader(io.StringIO(resp.text)))
            if not rows or not rows[0]:
                continue
            cell = rows[0][0] if rows[0] else ""
            parsed = _parse_year_month_from_cell(cell, now)
            if not parsed:
                continue
            year, month = parsed
            # Only include current and future months
            if year < now.year:
                continue
            if year == now.year and month < now.month:
                continue
            events = _scrape_one_sheet(sheet_id, gid, year, month, today, rows=rows)
            all_events.extend(events)
        except Exception:
            continue

    return all_events
