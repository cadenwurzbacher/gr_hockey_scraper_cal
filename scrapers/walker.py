"""Walker Ice & Fitness scraper."""

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

BASE_URL = "https://www.walkericeandfitness.com"
CALENDAR_URL = f"{BASE_URL}/calendar.aspx"
VENUE_ID = "walker"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]

# Match "March 6, 2026, 12:00 PM - 1:50 PM" or "12:00 PM - 1:50 PM"
TIME_RANGE_RE = re.compile(
    r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*[-–]\s*(\d{1,2}):(\d{2})\s*(AM|PM)",
    re.I,
)
ISO_RE = re.compile(r"202\d-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?")


def _parse_end_time(text: str, start_dt: datetime) -> datetime | None:
    """Parse end time from '12:00 PM - 1:50 PM'."""
    m = TIME_RANGE_RE.search(text)
    if not m:
        return None
    _, _, _, eh, em, eamp = m.groups()
    eh, em = int(eh), int(em)
    if eamp and eamp.upper() == "PM" and eh != 12:
        eh += 12
    elif eamp and eamp.upper() == "AM" and eh == 12:
        eh = 0
    return start_dt.replace(hour=eh, minute=em, second=0, microsecond=0)


def scrape() -> list[Event]:
    """Scrape Walker Ice & Fitness for Stick & Puck and Open Hockey."""
    events = []
    now = datetime.now(EASTERN_TZ)
    year, month = now.year, now.month

    for _ in range(4):
        resp = requests.get(
            CALENDAR_URL,
            params={"view": "list", "year": year, "month": month},
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for li in soup.find_all("li"):
            text = li.get_text(separator=" ", strip=True)
            if not is_stick_and_puck_or_open_hockey(text):
                continue
            if "Open Skate" in text and "Open Hockey" not in text:
                continue

            title = ""
            for h in li.find_all(["h3", "h4"]):
                t = h.get_text(strip=True)
                if is_stick_and_puck_or_open_hockey(t):
                    if is_youth_only_stick_and_puck(t):
                        break
                    title = t
                    break
            if not title:
                continue

            iso_match = ISO_RE.search(text)
            if not iso_match:
                continue
            iso_str = iso_match.group()
            if len(iso_str) == 16:  # 2026-03-20T12:00
                iso_str += ":00"
            start = datetime.fromisoformat(iso_str).replace(tzinfo=EASTERN_TZ)
            end = _parse_end_time(text, start)
            if not end:
                end = start  # fallback
            elif end <= start:
                end = start.replace(hour=start.hour + 1, minute=start.minute)  # 1 hr default

            more_link = li.find("a", href=re.compile(r"EID=\d+"))
            event_url = more_link.get("href", CALENDAR_URL) if more_link else CALENDAR_URL
            if event_url.startswith("/"):
                event_url = BASE_URL + event_url

            events.append(
                Event(
                    venue=VENUE_NAME,
                    title=title,
                    start=start,
                    end=end,
                    url=event_url,
                    source_id=f"walker-{start.strftime('%Y%m%d')}-{title[:25]}",
                    location=ADDRESS,
                )
            )

        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1

    return events
