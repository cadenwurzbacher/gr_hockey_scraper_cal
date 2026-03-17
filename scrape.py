#!/usr/bin/env python3
"""CLI entrypoint: run all scrapers, merge, generate ICS."""

import logging
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrapers.base import Event
from merge import merge, load_events, OUTPUT_DIR
from ical_gen import run as run_ical

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def run_scrapers() -> dict[str, list]:
    """Run each scraper; on success add to result, on failure keep existing."""
    from merge import load_events

    results = {}
    existing = load_events()

    scrapers = [
        ("patterson", "scrapers.patterson", "scrape"),
        ("walker", "scrapers.walker", "scrape"),
        ("griffs_belknap", "scrapers.griffs_belknap", "scrape"),
        ("griffs_georgetown", "scrapers.griffs_georgetown", "scrape"),
        ("southside", "scrapers.southside", "scrape"),
        ("eagles", "scrapers.eagles", "scrape"),
        ("cedar_rock", "scrapers.cedar_rock", "scrape"),
    ]

    for venue_id, mod_name, func_name in scrapers:
        try:
            mod = __import__(mod_name, fromlist=[func_name])
            fn = getattr(mod, func_name)
            events = fn()
            results[venue_id] = events
            log.info("%s: %d events", venue_id, len(events))
        except Exception as e:
            log.warning("%s: failed - %s", venue_id, e)
            if venue_id in existing:
                results[venue_id] = [Event.from_dict(ev) for ev in existing[venue_id]]
                log.info("%s: using %d cached events", venue_id, len(results[venue_id]))

    return results


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    by_venue = run_scrapers()
    merge(by_venue)
    run_ical()
    log.info("Done. ICS: %s", OUTPUT_DIR / "gr-hockey.ics")


if __name__ == "__main__":
    main()
