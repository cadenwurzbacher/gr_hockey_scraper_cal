"""Base scraper utilities: Event dataclass and filters."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import re

EASTERN_TZ = ZoneInfo("America/New_York")

EASTERN = "America/New_York"

# Exclude: open skate, freestyle, figure skating, learn to skate
EXCLUDE_PATTERNS = (
    r"open\s+skate",
    r"freestyle",
    r"figure\s+skat",
    r"learn\s+to\s+skate",
    r"learn\s+to\s+play",
    r"cross\s+ice",
    r"synchronized",
)

# Include: stick, puck, s&p, open hockey, available ice
INCLUDE_PATTERNS = (
    r"stick",
    r"puck",
    r"s\s*&\s*p",
    r"s&p",
    r"open\s+hockey",
    r"available\s+ice",
)

# Youth-only Stick & Puck: skip these
YOUTH_SKIP_PATTERNS = (
    r"12u\b",
    r"12\s*&\s*under",
    r"13u\b",
    r"13\s*&\s*under",
    r"14u\b",
    r"14\s*&\s*under",
    r"10u\b",
    r"10\s*&\s*under",
    r"8u\b",
    r"8\s*&\s*under",
    r"6u\b",
)


@dataclass
class Event:
    """A stick & puck or open hockey event."""

    venue: str
    title: str
    start: datetime
    end: datetime
    url: str
    source_id: str
    location: str

    def to_dict(self) -> dict:
        return {
            "venue": self.venue,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "url": self.url,
            "source_id": self.source_id,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        start = datetime.fromisoformat(d["start"])
        end = datetime.fromisoformat(d["end"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=EASTERN_TZ)
        if end.tzinfo is None:
            end = end.replace(tzinfo=EASTERN_TZ)
        return cls(
            venue=d["venue"],
            title=d["title"],
            start=start,
            end=end,
            url=d["url"],
            source_id=d["source_id"],
            location=d["location"],
        )


def is_stick_and_puck_or_open_hockey(title: str) -> bool:
    """Return True if the event should be included (S&P or Open Hockey)."""
    t = title.lower()
    for p in EXCLUDE_PATTERNS:
        if re.search(p, t, re.I):
            return False
    for p in INCLUDE_PATTERNS:
        if re.search(p, t, re.I):
            return True
    return False


def is_youth_only_stick_and_puck(title: str) -> bool:
    """Return True if this Stick & Puck is kids-only and should be skipped."""
    if not any(re.search(p, title, re.I) for p in ("stick", "puck", "s&p", r"s\s*&\s*p")):
        return False  # Not a stick & puck, don't filter
    t = title.lower()
    for p in YOUTH_SKIP_PATTERNS:
        if re.search(p, t, re.I):
            return True
    return False


def make_uid(venue_slug: str, dt: datetime, title: str) -> str:
    """Generate stable UID for calendar events."""
    norm = re.sub(r"[^a-z0-9]", "-", title.lower())[:40]
    date_str = dt.strftime("%Y%m%d%H%M")
    return f"{venue_slug}-{date_str}-{norm}@gr-hockey-scraper"
