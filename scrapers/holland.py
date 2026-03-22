"""Holland Ice Arena (Griff's IceHouse West) scraper.

Schedule is in a published Google Sheet, same format as Griff's Belknap:
- Row 0: date range
- Row 2: Start Date, Space, Event Name, Time
- Rows 3+: Start Date (e.g. "Sun, Mar 22"), Space, Event Name, Time ("4:00 PM - 4:50 PM")
"""

import csv
import io
import re
from datetime import datetime

import requests

from config import VENUES
from scrapers.base import (
    EASTERN_TZ,
    Event,
    is_stick_and_puck_or_open_hockey,
    is_youth_only_stick_and_puck,
    make_uid,
)

VENUE_ID = "holland"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQlJw5i-HW7Xk12YWbx13rnzm5oyosKm5SdKEJ6kSW87bLW0mR2M-Fxy37kIsQS3wkpIneTiRZWWXCY/pub?gid=433713822&single=true&output=csv"

MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_year_from_header(header_cell: str, now: datetime) -> int:
    m = re.search(r"(\d{4})", header_cell)
    if m:
        return int(m.group(1))
    return now.year


def _parse_date_cell(s: str, year: int) -> tuple[int, int, int] | None:
    s = s.strip()
    m = re.match(r"\w+,?\s+(\w+)\s+(\d{1,2})", s, re.I)
    if not m:
        return None
    month_str = m.group(1).lower()[:3]
    day = int(m.group(2))
    month = MONTH_ABBR.get(month_str)
    if not month or not 1 <= day <= 31:
        return None
    return year, month, day


def _parse_time_range(s: str, year: int, month: int, day: int) -> tuple[datetime, datetime] | None:
    s = s.strip()
    m = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)?\s*[-–]\s*(\d{1,2}):(\d{2})\s*(AM|PM)?", s, re.I)
    if not m:
        return None
    sh, sm = int(m.group(1)), int(m.group(2))
    samp = (m.group(3) or "AM").upper()
    eh, em = int(m.group(4)), int(m.group(5))
    eamp = (m.group(6) or samp).upper()
    if samp == "PM" and sh != 12:
        sh += 12
    elif samp == "AM" and sh == 12:
        sh = 0
    if eamp == "PM" and eh != 12:
        eh += 12
    elif eamp == "AM" and eh == 12:
        eh = 0
    try:
        start = datetime(year, month, day, sh, sm, tzinfo=EASTERN_TZ)
        end = datetime(year, month, day, eh, em, tzinfo=EASTERN_TZ)
        if end > start:
            return start, end
    except ValueError:
        pass
    return None


def scrape() -> list[Event]:
    """Scrape Holland Ice Arena from published Google Sheet."""
    try:
        resp = requests.get(SHEET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        rows = list(csv.reader(io.StringIO(resp.text)))
    except Exception:
        return []

    if len(rows) < 4:
        return []

    now = datetime.now(EASTERN_TZ)
    today = now.date()
    year = _parse_year_from_header(rows[0][2] if len(rows[0]) > 2 else "", now)
    events = []

    for row in rows[3:]:
        if len(row) < 6:
            continue
        date_s = row[2].strip()
        space = row[3].strip()
        name = row[4].strip()
        time_s = row[5].strip()
        if not date_s or not name or not time_s:
            continue
        parsed = _parse_date_cell(date_s, year)
        if not parsed:
            continue
        year, month, day = parsed
        try:
            event_date = datetime(year, month, day, tzinfo=EASTERN_TZ).date()
        except ValueError:
            continue
        if event_date < today:
            continue
        if not is_stick_and_puck_or_open_hockey(name):
            continue
        if is_youth_only_stick_and_puck(name):
            continue
        times = _parse_time_range(time_s, year, month, day)
        if not times:
            continue
        start_dt, end_dt = times
        rink = f" ({space})" if space else ""
        title = f"{name}{rink}"
        events.append(Event(
            venue=VENUE_NAME,
            title=title,
            start=start_dt,
            end=end_dt,
            url="https://www.griffswest.com/",
            source_id=make_uid(VENUE_ID, start_dt, title),
            location=ADDRESS,
        ))

    return events
