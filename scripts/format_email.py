#!/usr/bin/env python3
"""Format the scrape report as email body. Called by GitHub Actions."""

import json
import sys
from pathlib import Path

REPORT_FILE = Path(__file__).resolve().parent.parent / "output" / "report.json"


def main() -> None:
    if not REPORT_FILE.exists():
        print("GR Hockey Calendar – No report found (scrape may have failed early).")
        sys.exit(0)

    with open(REPORT_FILE) as f:
        report = json.load(f)

    success = report.get("success", [])
    failed = report.get("failed", [])
    new_events = report.get("new_events", [])
    new_count = report.get("new_count", 0)

    lines = [
        "GR Hockey Calendar – Daily Scrape Report",
        "",
        "--- Scrapers ---",
        f"✓ Working: {', '.join(success) if success else 'none'}",
        "",
    ]
    if failed:
        lines.append("✗ Failed:")
        for f in failed:
            err = f["error"]
            lines.append(f"  • {f['venue']}: {err[:100]}{'...' if len(err) > 100 else ''}")
        lines.append("")
    else:
        lines.append("✗ Failed: none")
        lines.append("")

    lines.append("--- New events (not previously in calendar) ---")
    if new_count == 0:
        lines.append("None")
    else:
        lines.append(f"({new_count} new)")
        for ev in new_events[:25]:
            lines.append(f"  • {ev['venue']}: {ev['title']}")
            lines.append(f"    {ev['start']} – {ev['end']}")
        if new_count > 25:
            lines.append(f"  ... and {new_count - 25} more")
    lines.append("")
    lines.append("Subscribe: https://cadenwurzbacher.github.io/gr_hockey_scraper_cal/output/gr-hockey.ics")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
