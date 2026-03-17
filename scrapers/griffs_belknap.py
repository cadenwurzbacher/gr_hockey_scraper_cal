"""Griff's IceHouse (Belknap) scraper.

Schedule is in an embedded published Google Sheet. Use MONTHLY and QUARTERLY tabs -
Daily/Weekly tabs don't have full Stick & Puck data.

Shared format:
- Row 0: date range "17th March - 17th April 2026"
- Row 2: Start Date, Space, Event Name, Time, Maintenance?, Sport
- Rows 3+: Start Date (e.g. "Tue, Mar 17"), Space, Event Name, Time ("4:00 PM - 5:00 PM")
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

VENUE_ID = "griffs_belknap"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]
BASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR6_TDKpbGeNl6UGe2y2go2-jaFm45_hbcfwNdCmKWEDpQFmOK9JsYvWvgvoOSgrhKDng2OEFFdwQ-c/pub?gid={}&single=true&output=csv"
MONTHLY_GID = 433713822
QUARTERLY_GID = 1321684532

MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_year_from_header(header_cell: str, now: datetime) -> int:
    """Extract year from '17th March - 17th April 2026' or similar."""
    m = re.search(r"(\d{4})", header_cell)
    if m:
        return int(m.group(1))
    return now.year


def _parse_date_cell(s: str, year: int) -> tuple[int, int, int] | None:
    """Parse 'Tue, Mar 17' -> (year, month, day)."""
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
    """Parse '4:00 PM - 5:00 PM' into (start_dt, end_dt)."""
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


def _parse_row(row: list[str], year: int, today: datetime) -> Event | None:
    """Parse one Monthly tab row. Cols 2,3,4,5 = Start Date, Space, Event Name, Time."""
    if len(row) < 6:
        return None
    date_s = row[2].strip()
    space = row[3].strip()
    name = row[4].strip()
    time_s = row[5].strip()
    if not date_s or not name or not time_s:
        return None
    parsed = _parse_date_cell(date_s, year)
    if not parsed:
        return None
    year, month, day = parsed
    try:
        event_date = datetime(year, month, day, tzinfo=EASTERN_TZ).date()
    except ValueError:
        return None
    if event_date < today:
        return None
    if not is_stick_and_puck_or_open_hockey(name):
        return None
    if is_youth_only_stick_and_puck(name):
        return None
    times = _parse_time_range(time_s, year, month, day)
    if not times:
        return None
    start_dt, end_dt = times
    rink = f" ({space})" if space else ""
    title = f"{name}{rink}"
    return Event(
        venue=VENUE_NAME,
        title=title,
        start=start_dt,
        end=end_dt,
        url="https://www.griffsicehouse.com/ice-schedule-2/",
        source_id=make_uid(VENUE_ID, start_dt, title),
        location=ADDRESS,
    )


def _scrape_tab(gid: int, now: datetime, today) -> list[Event]:
    """Scrape one tab (Monthly or Quarterly) and return events."""
    try:
        resp = requests.get(BASE_URL.format(gid), headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        rows = list(csv.reader(io.StringIO(resp.text)))
    except Exception:
        return []
    if len(rows) < 4:
        return []
    year = _parse_year_from_header(rows[0][2] if len(rows[0]) > 2 else "", now)
    events = []
    for row in rows[3:]:
        if len(row) < 6:
            continue
        ev = _parse_row(row, year, today)
        if ev:
            events.append(ev)
    return events


def scrape() -> list[Event]:
    """Scrape Griff's IceHouse Belknap from Monthly and Quarterly Schedule tabs."""
    now = datetime.now(EASTERN_TZ)
    today = now.date()
    seen = set()
    events = []
    for gid in (MONTHLY_GID, QUARTERLY_GID):
        for ev in _scrape_tab(gid, now, today):
            if ev.source_id not in seen:
                seen.add(ev.source_id)
                events.append(ev)
    return events
