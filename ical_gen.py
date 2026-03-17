"""Generate ICS calendar from events."""

from datetime import datetime
from pathlib import Path
import json

from zoneinfo import ZoneInfo

from scrapers.base import Event, make_uid, EASTERN

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
ICS_FILE = OUTPUT_DIR / "gr-hockey.ics"
EVENTS_FILE = OUTPUT_DIR / "events.json"

EASTERN_TZ = ZoneInfo(EASTERN)


def filter_today_and_later(events: list[dict]) -> list[dict]:
    """Drop events before today (Eastern midnight)."""
    now = datetime.now(EASTERN_TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return [e for e in events if datetime.fromisoformat(e["start"]).astimezone(EASTERN_TZ) >= today_start]


def generate_ics(events: list[dict]) -> str:
    """Generate ICS content from event dicts."""
    from ics import Calendar, Event as ICSEvent

    cal = Calendar()
    for e in events:
        start = datetime.fromisoformat(e["start"])
        end = datetime.fromisoformat(e["end"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=EASTERN_TZ)
        if end.tzinfo is None:
            end = end.replace(tzinfo=EASTERN_TZ)

        ev = ICSEvent()
        ev.name = f"{e['title']} @ {e['venue']}"
        ev.begin = start
        ev.end = end
        ev.location = e.get("location", "")
        ev.description = e.get("url", "")
        ev.uid = make_uid(e["venue"].lower().replace(" ", "-")[:20], start, e["title"])
        cal.events.add(ev)

    return cal.serialize()


def run() -> None:
    """Load merged events, filter, generate ICS."""
    if not EVENTS_FILE.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(ICS_FILE, "w") as f:
            f.write("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//GR Hockey Scraper//EN\nEND:VCALENDAR\n")
        return

    with open(EVENTS_FILE) as f:
        by_venue = json.load(f)

    all_events = []
    for venue, events in by_venue.items():
        all_events.extend(events)

    filtered = filter_today_and_later(all_events)
    filtered.sort(key=lambda e: e["start"])

    ics_content = generate_ics(filtered)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(ICS_FILE, "w") as f:
        f.write(ics_content)
