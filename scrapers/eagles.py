"""Eagles Ice Center scraper.

Eagles Ice Center does not offer Stick & Puck or Open Hockey.
Website: "We do not offer open skating or drop-in hockey at this time."
https://eaglesicecenter.com
"""

from config import VENUES
from scrapers.base import Event

VENUE_ID = "eagles"
VENUE_NAME = VENUES[VENUE_ID]["name"]
ADDRESS = VENUES[VENUE_ID]["address"]
URL = "https://eaglesicecenter.com/calendar"


def scrape() -> list[Event]:
    """Scrape Eagles Ice Center. Returns [] - no S&P or Open Hockey offered."""
    return []
