"""Venue configuration: addresses and scrape URLs."""

VENUES = {
    "griffs_belknap": {
        "name": "Griff's IceHouse (Belknap)",
        "address": "30 Coldbrook St NE, Grand Rapids, MI",
    },
    "walker": {
        "name": "Walker Ice & Fitness",
        "address": "4151 Remembrance Rd NW, Walker, MI",
    },
    "patterson": {
        "name": "Patterson Ice Center",
        "address": "2550 Patterson Ave SE, Grand Rapids, MI",
    },
    "griffs_georgetown": {
        "name": "Hudsonville Ice Arena",
        "address": "8500 48th Ave, Hudsonville, MI",
    },
    "southside": {
        "name": "Southside Ice Arena",
        "address": "566 100th St SW, Byron Center, MI 49315",
    },
    "eagles": {
        "name": "Eagles Ice Center",
        "address": "2600 Village Drive SE, Grand Rapids, MI 49506",
    },
    "cedar_rock": {
        "name": "Cedar Rock Sportsplex",
        "address": "4758 Cornfield Drive NE, Cedar Springs, MI 49319",
    },
}

CEDAR_ROCK_SHEET_URL = "https://docs.google.com/spreadsheets/d/1rLaoKgECpzthOg7w9og17OZuN30uTvoiRX56jSo7DOA"
# Export without gid returns the current month tab (default view).
# Add gids here for future months: open each tab, copy #gid=XXX from URL.
# GOOGLE_SHEETS_API_KEY enables auto-discovery of all tabs.
CEDAR_ROCK_GIDS = []  # Optional: future month gids (April, May, etc.)
GOOGLE_SHEETS_API_KEY = ""  # Optional: for auto-discovering all sheet gids
