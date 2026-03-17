# GR Hockey Stick & Puck / Open Hockey Calendar

Scrapes Stick & Puck and Open Hockey sessions from 7 Grand Rapids-area ice rinks and publishes a subscribable iCal feed.

## Subscribe

After deploying, add this URL to Google Calendar, Apple Calendar, or any iCal client:

```
https://cadenwurzbacher.github.io/gr_hockey_scraper_cal/output/gr-hockey.ics
```

## Local Usage

```bash
pip install -r requirements.txt
python scrape.py
```

Outputs:
- `output/gr-hockey.ics` – iCal feed
- `output/events.json` – cached state (used when a scraper fails)

## Rinks

| Rink | Status |
|------|--------|
| Patterson Ice Center | Working |
| Walker Ice & Fitness | Working |
| Griff's IceHouse (Belknap) | Working (Google Sheet Monthly tab) |
| Hudsonville Ice Arena | Working (BondSports API) |
| Southside Ice Arena | Working (rectimes API) |
| Eagles Ice Center | No S&P/Open Hockey offered |
| Cedar Rock Sportsplex | Working (Google Sheet; keep sheet updated with current month) |

## Cedar Rock Google Sheet

Cedar Rock uses a view-only Google Sheet with **multiple month tabs**. The scraper uses current and future months only. Past tabs often have year in the name (e.g. "February 2026"); the current tab may not (e.g. "March").

**Current month:** The base URL (no `gid`) exports the default/current month tab. The scraper uses this first – no config needed for the current month.

**Future months:** Add gids to `CEDAR_ROCK_GIDS` or set `GOOGLE_SHEETS_API_KEY` for auto-discovery of all tabs.

## GitHub Actions

The workflow runs daily at 6 AM Eastern and on manual trigger. It commits `output/gr-hockey.ics` and `output/events.json` so the calendar stays updated. It also sends a daily email report to `caden@cadenwurzbacher.com` with scraper status and new events.

**Email secrets (repo Settings → Secrets):**
- `SMTP_USER` – Gmail address (e.g. `caden@cadenwurzbacher.com`)
- `SMTP_PASSWORD` – [Gmail app password](https://myaccount.google.com/apppasswords) (not your regular password)

## GitHub Pages

1. Repo → Settings → Pages
2. Source: Deploy from a branch
3. Branch: main, folder: / (root)
4. Subscribe URL: `https://cadenwurzbacher.github.io/gr_hockey_scraper_cal/output/gr-hockey.ics`
