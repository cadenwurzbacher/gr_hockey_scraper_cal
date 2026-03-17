#!/usr/bin/env python3
"""CLI entrypoint: run all scrapers, merge, generate ICS."""

import json
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

REPORT_FILE = OUTPUT_DIR / "report.json"


def run_scrapers() -> tuple[dict[str, list], list[str], list[tuple[str, str]]]:
    """Run each scraper; on success add to result, on failure keep existing.
    Returns (results, success_list, failed_list with errors).
    """
    results = {}
    success = []
    failed = []
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
            success.append(venue_id)
            log.info("%s: %d events", venue_id, len(events))
        except Exception as e:
            err_msg = str(e)
            failed.append((venue_id, err_msg))
            log.warning("%s: failed - %s", venue_id, e)
            if venue_id in existing:
                results[venue_id] = [Event.from_dict(ev) for ev in existing[venue_id]]
                log.info("%s: using %d cached events", venue_id, len(results[venue_id]))

    return results, success, failed


def _existing_source_ids(by_venue: dict[str, list[dict]]) -> set[str]:
    ids = set()
    for events in by_venue.values():
        for ev in events:
            sid = ev.get("source_id")
            if sid:
                ids.add(sid)
    return ids


def _new_events_summary(by_venue: dict[str, list[Event]], existing_ids: set[str]) -> list[dict]:
    """Events in by_venue whose source_id is not in existing_ids."""
    new = []
    for venue, events in by_venue.items():
        for ev in events:
            if ev.source_id not in existing_ids:
                new.append({
                    "venue": ev.venue,
                    "title": ev.title,
                    "start": ev.start.strftime("%Y-%m-%d %H:%M"),
                    "end": ev.end.strftime("%Y-%m-%d %H:%M"),
                })
    return new


def write_report(
    success: list[str],
    failed: list[tuple[str, str]],
    new_events: list[dict],
) -> None:
    """Write report.json for the workflow email step."""
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump({
            "success": success,
            "failed": [{"venue": v, "error": e} for v, e in failed],
            "new_events": new_events,
            "new_count": len(new_events),
        }, f, indent=2)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing_before = load_events()
    existing_ids = _existing_source_ids(existing_before)

    by_venue, success, failed = run_scrapers()
    merge(by_venue)
    run_ical()
    log.info("Done. ICS: %s", OUTPUT_DIR / "gr-hockey.ics")

    # Build new-events list from merged output (Event objects)
    by_venue_events = {}
    for venue_id, events in by_venue.items():
        by_venue_events[venue_id] = events
    new_events = _new_events_summary(by_venue_events, existing_ids)
    write_report(success, failed, new_events)
    log.info("Report: %d new events", len(new_events))
    log.info("Report written to %s", REPORT_FILE)


if __name__ == "__main__":
    main()
