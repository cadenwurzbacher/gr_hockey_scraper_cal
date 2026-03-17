"""Merge logic: per-venue replace on success, keep on failure."""

import json
from datetime import datetime
from pathlib import Path

from zoneinfo import ZoneInfo

from scrapers.base import Event

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
EVENTS_FILE = OUTPUT_DIR / "events.json"
EASTERN = ZoneInfo("America/New_York")


def _today_start() -> datetime:
    now = datetime.now(EASTERN)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _filter_today_and_later(events: list[Event]) -> list[Event]:
    today = _today_start()
    return [e for e in events if e.start.astimezone(EASTERN) >= today]


def load_events() -> dict[str, list[dict]]:
    """Load events by venue from disk."""
    if not EVENTS_FILE.exists():
        return {}
    with open(EVENTS_FILE) as f:
        return json.load(f)


def save_events(by_venue: dict[str, list[dict]]) -> None:
    """Save events by venue to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_FILE, "w") as f:
        json.dump(by_venue, f, indent=2)


def merge(by_venue: dict[str, list[Event]]) -> None:
    """Merge new scraped events with existing state and save.
    - On success for a venue: replace that venue's events (filtered to today+).
    - On failure (venue not in by_venue): keep existing.
    """
    existing = load_events()
    for venue, events in by_venue.items():
        filtered = _filter_today_and_later(events)
        existing[venue] = [e.to_dict() for e in filtered]
    save_events(existing)
