"""Patterson Ice Center scraper."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from config import VENUES
from scrapers.base import (
    Event,
    EASTERN_TZ,
    is_stick_and_puck_or_open_hockey,
    is_youth_only_stick_and_puck,
)

BASE_URL = "https://www.pattersonicecenter.com"
MONTH_LIST_URL = f"{BASE_URL}/event/show_month_list/8350407"
VENUE_ID = "patterson"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]

MONTH_ABBR = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
TIME_RE = re.compile(r"(\d{1,2}):?(\d{2})?\s*(am|pm)\s*(EST|EDT)?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(am|pm)\s*(EST|EDT)?", re.I)


def _parse_time_range(text: str, year: int, month: int, day: int) -> tuple[datetime, datetime] | None:
    """Parse 'Sunday, 9:45am EST - 10:45am EST' into start, end datetimes."""
    m = TIME_RE.search(text)
    if not m:
        return None
    sh, sm, samp, _, eh, em, eamp, _ = m.groups()
    sh, sm = int(sh), int(sm or 0)
    eh, em = int(eh), int(em or 0)
    if samp and samp.lower() == "pm" and sh != 12:
        sh += 12
    elif samp and samp.lower() == "am" and sh == 12:
        sh = 0
    if eamp and eamp.lower() == "pm" and eh != 12:
        eh += 12
    elif eamp and eamp.lower() == "am" and eh == 12:
        eh = 0
    start = datetime(year, month, day, sh, sm, tzinfo=EASTERN_TZ)
    end = datetime(year, month, day, eh, em, tzinfo=EASTERN_TZ)
    return start, end


def _parse_day_from_vevent(vevent) -> int | None:
    """Get day from vevent text if present. First event of each day has 'Mar1', 'Mar2', etc."""
    text = vevent.get_text(strip=True)
    for abbr in MONTH_ABBR:
        if abbr in text:
            rest = text.split(abbr, 1)[-1]
            m = re.search(r"^(\d{1,2})", rest)
            if m:
                return int(m.group(1))
    return None


def scrape() -> list[Event]:
    """Scrape Patterson Ice Center for Stick & Puck and Open Hockey."""
    events = []
    now = datetime.now(EASTERN_TZ)
    year, month = now.year, now.month
    seen = set()  # Dedupe by (year, month, day, title, start)

    for _ in range(4):
        resp = requests.get(MONTH_LIST_URL, params={"year": year, "month": month}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for agg in soup.find_all("div", class_="eventAggregatorElement"):
            current_day = None
            for vevent in agg.find_all("div", class_="vevent"):
                day_from_vevent = _parse_day_from_vevent(vevent)
                if day_from_vevent is not None:
                    current_day = day_from_vevent
                if current_day is None:
                    continue

                h5 = vevent.find("h5", class_="summary")
                if not h5:
                    continue
                title = h5.get_text(strip=True)
                if not is_stick_and_puck_or_open_hockey(title):
                    continue
                if is_youth_only_stick_and_puck(title):
                    continue

                parent_text = vevent.get_text(separator=" ", strip=True)
                try:
                    parsed = _parse_time_range(parent_text, year, month, current_day)
                except ValueError:
                    continue
                if not parsed:
                    continue
                start, end = parsed

                key = (year, month, current_day, title, start.isoformat())
                if key in seen:
                    continue
                seen.add(key)

                event_url = f"{BASE_URL}/event/8350407/{year}/{month}/{current_day}"
                events.append(
                    Event(
                        venue=VENUE_NAME,
                        title=title,
                        start=start,
                        end=end,
                        url=event_url,
                        source_id=f"patterson-{year}-{month}-{current_day}-{title[:30]}",
                        location=ADDRESS,
                    )
                )

        # Next month
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1

    return events
