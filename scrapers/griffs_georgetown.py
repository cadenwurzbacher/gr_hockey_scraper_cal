"""Hudsonville Ice Arena scraper (BondSports).

Schedule is served via JSON API - no Playwright needed.
API: https://schedule.bondsports.co/api/schedule/Hudsonville-Ice-Schedule
"""

import re
from datetime import datetime

import requests

from config import VENUES
from scrapers.base import EASTERN_TZ, Event, is_youth_only_stick_and_puck, make_uid

VENUE_ID = "griffs_georgetown"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]
URL = "https://schedule.bondsports.co/schedule/Hudsonville-Ice-Schedule"
API_URL = "https://schedule.bondsports.co/api/schedule/Hudsonville-Ice-Schedule"


def _is_snp_or_open_hockey(title: str) -> bool:
    """Match Stick & Puck / Open Hockey; exclude league games (contain ' vs ')."""
    t = title.strip()
    if " vs " in t.lower():
        return False
    t_lower = t.lower()
    if re.search(r"stick\s*&\s*puck|stick\s+and\s+puck", t_lower):
        return True
    if "open hockey" in t_lower:
        return True
    return False


def _parse_slot(slot: dict, today) -> Event | None:
    """Convert API slot to Event, or None if skip."""
    title = (slot.get("title") or "").strip()
    if not _is_snp_or_open_hockey(title):
        return None
    if is_youth_only_stick_and_puck(title):
        return None

    start_date = slot.get("startDate")  # "2026-03-18T00:00:00.000Z"
    start_time = slot.get("startTime")  # "15:00:00"
    end_time = slot.get("endTime")      # "15:50:00"
    if not all([start_date, start_time, end_time]):
        return None

    # Parse date (YYYY-MM-DD)
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", start_date)
    if not m:
        return None
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        event_date = datetime(year, month, day, tzinfo=EASTERN_TZ).date()
    except ValueError:
        return None
    if event_date < today:
        return None

    # Parse times (HH:MM:SS)
    def parse_time(ts: str) -> tuple[int, int] | None:
        mm = re.match(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", ts)
        if mm:
            return int(mm.group(1)), int(mm.group(2))
        return None

    st = parse_time(start_time)
    et = parse_time(end_time)
    if not st or not et:
        return None
    start_dt = datetime(year, month, day, st[0], st[1], tzinfo=EASTERN_TZ)
    end_dt = datetime(year, month, day, et[0], et[1], tzinfo=EASTERN_TZ)
    if end_dt <= start_dt:
        return None

    space = (slot.get("space") or {}).get("name") or ""
    rink = f" ({space})" if space else ""
    full_title = f"{title}{rink}"

    return Event(
        venue=VENUE_NAME,
        title=full_title,
        start=start_dt,
        end=end_dt,
        url=URL,
        source_id=make_uid(VENUE_ID, start_dt, full_title),
        location=ADDRESS,
    )


def scrape() -> list[Event]:
    """Scrape Hudsonville Ice Arena from BondSports API."""
    try:
        resp = requests.get(
            API_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    slots = data.get("slots") or []
    today = datetime.now(EASTERN_TZ).date()
    events = []
    for slot in slots:
        ev = _parse_slot(slot, today)
        if ev:
            events.append(ev)
    return events
