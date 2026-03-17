"""Southside Ice Arena scraper.

Schedule via LeagueApps/rectimes API.
API: POST to api.rectimes.com/api/v1/facilities/southsidearena/bookings/get_for_calendar
"""

import re
from datetime import datetime, timedelta, time

import requests

from config import VENUES
from scrapers.base import EASTERN_TZ, Event, is_stick_and_puck_or_open_hockey, is_youth_only_stick_and_puck, make_uid

VENUE_ID = "southside"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]
URL = "https://facilities.leagueapps.com/southsidearena"
API_URL = "https://api.rectimes.com/api/v1/facilities/southsidearena/bookings/get_for_calendar"
VENUE_IDS = [2044, 2045, 2046, 2047, 2048, 2049, 2050]


def _parse_booking(item: dict, today) -> Event | None:
    """Convert API booking to Event, or None if skip."""
    group = (item.get("groupName") or "").strip()
    event_name = (item.get("eventName") or "").strip()
    title = f"{group} - {event_name}".strip(" -") or group or event_name
    if not title:
        return None
    if not is_stick_and_puck_or_open_hockey(title):
        return None
    if is_youth_only_stick_and_puck(title):
        return None

    start_s = item.get("startTimeLocal")  # "2026-03-16T10:00:00"
    end_s = item.get("endTimeLocal")
    if not start_s or not end_s:
        return None

    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", start_s)
    if not m:
        return None
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    sh, sm = int(m.group(4)), int(m.group(5))
    m2 = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", end_s)
    if not m2:
        return None
    eh, em = int(m2.group(4)), int(m2.group(5))

    try:
        start_dt = datetime(year, month, day, sh, sm, tzinfo=EASTERN_TZ)
        end_dt = datetime(year, month, day, eh, em, tzinfo=EASTERN_TZ)
    except ValueError:
        return None
    if start_dt.date() < today:
        return None
    if end_dt <= start_dt:
        return None

    rink = (item.get("venueName") or "").strip()
    full_title = f"{title} ({rink})" if rink else title
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
    """Scrape Southside Ice Arena from rectimes API."""
    today = datetime.now(EASTERN_TZ).date()
    all_events = []
    start_dt = datetime.combine(today, time.min).replace(tzinfo=EASTERN_TZ)

    for _ in range(8):
        end_dt = start_dt + timedelta(weeks=1)
        payload = {
            "venueIds": VENUE_IDS,
            "startTimeLocal": start_dt.strftime("%Y-%m-%dT00:00:00Z"),
            "endTimeLocal": end_dt.strftime("%Y-%m-%dT00:00:00Z"),
        }
        try:
            resp = requests.post(
                API_URL,
                json=payload,
                headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break
        for item in data:
            ev = _parse_booking(item, today)
            if ev:
                all_events.append(ev)
        start_dt = end_dt
        if start_dt.date() > today + timedelta(days=60):
            break

    return all_events
