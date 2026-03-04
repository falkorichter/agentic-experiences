#!/usr/bin/env python3
"""
Fetch Spreewölfe Berlin match schedules from bishl.de and generate iCal files.

This is a community project and is NOT affiliated with Spreewölfe Berlin e.V.
Schedule data is scraped from the publicly available BISHL website.

Usage:
    pip install requests beautifulsoup4
    python fetch_schedules.py

    # Fetch only a specific tournament:
    python fetch_schedules.py --tournament schuelerliga-lk2

    # Specify output directory:
    python fetch_schedules.py --output ./output

    # Specify year:
    python fetch_schedules.py --year 2026
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Install them with:")
    print("  pip install requests beautifulsoup4")
    sys.exit(1)

BISHL_BASE = "https://www.bishl.de"
TEAM_FILTER = "Spreewölfe"  # Only include games involving this team

# Known BISHL tournament slugs and their Spreewölfe team mapping.
# Update this list when new tournaments are added on bishl.de.
KNOWN_TOURNAMENTS = {
    "schuelerliga-lk2": {
        "name": "Schüler U-13",
        "short": "U13",
        "file_slug": "u13",
    },
    # Add more tournaments here as they appear on bishl.de, e.g.:
    # "jugendliga":       {"name": "Jugend U-16",  "short": "U16",  "file_slug": "u16"},
    # "herren-regionalliga": {"name": "Herren I", "short": "H1", "file_slug": "herren-i"},
    # "herren-landesliga": {"name": "Herren II", "short": "H2", "file_slug": "herren-ii"},
    # "damen-bundesliga": {"name": "Damen", "short": "D", "file_slug": "damen"},
    # "bambiniliga":      {"name": "Bambini U-10", "short": "U10", "file_slug": "u10"},
}

# Known venue addresses. The script uses these to enrich iCal LOCATION fields.
# Add new venues here as you discover them.
VENUE_ADDRESSES = {
    "Poststadion": "Lehrter Str. 59, 10557 Berlin",
    "Sporthalle Fredersdorf": "Posentsche Str. 60, 15370 Fredersdorf-Vogelsdorf",
    "Lilli Henoch Sporthalle": "Fritz-Lesch-Straße 32, 13053 Berlin",
    "Carl-Schuhmann-Halle": "Fritz-Lesch-Straße 35, 13053 Berlin",
    "Lupcom Arena": "Fritz-Triddelfitz-Weg 8, 18069 Rostock",
    "Falkensee": "Ruppiner Str. 25, 14612 Falkensee",
}

# German month abbreviations used by bishl.de
GERMAN_MONTHS = {
    "Jan.": "01", "Feb.": "02", "März": "03", "Apr.": "04",
    "Mai": "05", "Juni": "06", "Juli": "07", "Aug.": "08",
    "Sept.": "09", "Okt.": "10", "Nov.": "11", "Dez.": "12",
}


def fetch_page(url):
    """Fetch a page and return a BeautifulSoup object."""
    print(f"  Fetching {url} ...")
    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "SpreewoelfeCalendarBot/1.0 (community project)"
    })
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_bishl_date(date_text):
    """
    Parse a German date string from bishl.de.
    Examples: "Sonntag, 15. März 26, 12:00" -> (datetime, "12:00")
    """
    # Remove day name prefix
    text = re.sub(r"^[A-Za-zäöü]+,\s*", "", date_text.strip())

    # Match: "15. März 26, 12:00" or "4. Okt. 26, 11:00"
    m = re.match(r"(\d{1,2})\.\s+(\S+)\s+(\d{2,4}),\s*(\d{1,2}):(\d{2})", text)
    if not m:
        return None, None

    day = int(m.group(1))
    month_str = m.group(2)
    year_str = m.group(3)
    hour = int(m.group(4))
    minute = int(m.group(5))

    month = GERMAN_MONTHS.get(month_str)
    if not month:
        return None, None

    year = int(year_str)
    if year < 100:
        year += 2000

    dt = datetime(year, int(month), day, hour, minute)
    time_str = f"{hour:02d}:{minute:02d}"
    return dt, time_str


def parse_bishl_schedule(soup, tournament_info):
    """
    Parse the bishl.de tournament page and extract Spreewölfe games.
    Returns a list of event dicts with only Spreewölfe games.
    """
    events = []
    short = tournament_info["short"]

    # bishl.de uses a consistent structure with game cards/blocks.
    # We look for text content and parse it block by block.
    text = soup.get_text("\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for date lines like "Sonntag, 15. März 26, 12:00"
        dt, time_str = parse_bishl_date(line)
        if dt is None:
            i += 1
            continue

        # Next line should be venue
        venue = lines[i + 1] if i + 1 < len(lines) else "TBD"

        # Then home abbreviation, home name, away abbreviation, away name
        home_abbr = lines[i + 2] if i + 2 < len(lines) else ""
        home_name = lines[i + 3] if i + 3 < len(lines) else ""
        away_abbr = lines[i + 4] if i + 4 < len(lines) else ""
        away_name = lines[i + 5] if i + 5 < len(lines) else ""

        i += 6  # Move past this game block

        # Only include Spreewölfe games
        is_swb_home = TEAM_FILTER in home_name
        is_swb_away = TEAM_FILTER in away_name
        if not (is_swb_home or is_swb_away):
            continue

        # Build location with address if known
        location = venue
        for venue_name, address in VENUE_ADDRESSES.items():
            if venue_name.lower() in venue.lower():
                location = f"{venue}\\, {address}"
                break

        opponent = away_name if is_swb_home else home_name
        home_away = "Heimspiel" if is_swb_home else "Auswärtsspiel"
        summary = f"{short}: {home_name} vs {away_name}"

        uid = f"{short.lower()}-{dt.strftime('%Y%m%d-%H%M')}@bishl.de"

        events.append({
            "date": dt.strftime("%Y-%m-%d"),
            "time": time_str,
            "dt_start": dt.strftime("%Y%m%dT%H%M%S"),
            "dt_end": (dt + timedelta(minutes=50)).strftime("%Y%m%dT%H%M%S"),
            "home": home_name,
            "away": away_name,
            "opponent": opponent,
            "is_home": is_swb_home,
            "home_away": home_away,
            "venue": venue,
            "location": location,
            "summary": summary,
            "uid": uid,
        })

    return events


def generate_ical(events, tournament_info):
    """Generate iCalendar content from a list of events."""
    name = tournament_info["name"]
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//Spreewoelfe {name} Schedule//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Spreewölfe {name} {events[0]['date'][:4]}",
        f"X-WR-CALDESC:{name} - Spreewölfe Berlin (from bishl.de)",
    ]

    for event in events:
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{event['uid']}",
            f"DTSTAMP:{now}",
            f"DTSTART;TZID=Europe/Berlin:{event['dt_start']}",
            f"DTEND;TZID=Europe/Berlin:{event['dt_end']}",
            f"SUMMARY:{event['summary']}",
            f"LOCATION:{event['location']}",
            f"DESCRIPTION:{name}\\nQuelle: bishl.de",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def update_locations(events, locations_file):
    """Update the locations database with any new venues found."""
    if os.path.exists(locations_file):
        with open(locations_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"venues": [], "last_updated": "", "source": BISHL_BASE, "notes": ""}

    existing_names = {v["name"].lower() for v in data["venues"]}

    for event in events:
        venue = event.get("venue", "")
        if venue and venue.lower() not in existing_names:
            address = ""
            for vn, addr in VENUE_ADDRESSES.items():
                if vn.lower() in venue.lower():
                    address = addr
                    break
            data["venues"].append({
                "name": venue,
                "team_home": event.get("home", ""),
                "address": address,
                "notes": "auto-discovered from bishl.de",
            })
            existing_names.add(venue.lower())

    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    data["source"] = BISHL_BASE

    with open(locations_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Locations database updated: {len(data['venues'])} venues")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Spreewölfe Berlin schedules from bishl.de and generate iCal files."
    )
    parser.add_argument(
        "--tournament",
        help="Fetch only a specific tournament by slug (e.g. schuelerliga-lk2)",
    )
    parser.add_argument(
        "--year", type=int, default=datetime.now().year,
        help="Season year (default: current year)",
    )
    parser.add_argument(
        "--output", default=".",
        help="Output directory for generated files (default: current directory)",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    locations_file = os.path.join(args.output, "locations.json")

    tournaments = KNOWN_TOURNAMENTS.copy()
    if args.tournament:
        if args.tournament in tournaments:
            tournaments = {args.tournament: tournaments[args.tournament]}
        else:
            print(f"Unknown tournament: {args.tournament}")
            print(f"Available: {', '.join(tournaments.keys())}")
            sys.exit(1)

    all_events = []
    generated_files = []

    for slug, info in tournaments.items():
        url = f"{BISHL_BASE}/tournaments/{slug}/{args.year}"
        print(f"\nProcessing {info['name']} ({slug})...")

        try:
            soup = fetch_page(url)
        except requests.RequestException as e:
            print(f"  ERROR: Could not fetch {url}: {e}")
            continue

        events = parse_bishl_schedule(soup, info)
        print(f"  Found {len(events)} Spreewölfe games")

        if events:
            ical_content = generate_ical(events, info)
            filename = f"{args.year}-{info['file_slug']}.ics"
            filepath = os.path.join(args.output, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(ical_content)
            print(f"  Written: {filepath}")
            generated_files.append(filename)
            all_events.extend(events)
        else:
            print(f"  No Spreewölfe games found for {info['name']} in {args.year}")

    # Update locations database
    if all_events:
        update_locations(all_events, locations_file)

    # Summary
    print("\n" + "=" * 60)
    print(f"Done! Generated {len(generated_files)} iCal files "
          f"with {len(all_events)} Spreewölfe games.")
    if generated_files:
        print("Files:")
        for f in generated_files:
            print(f"  - {f}")
    else:
        print("No Spreewölfe games found.")
        print(f"Check {BISHL_BASE} manually for available tournaments.")
        print("You may need to add new tournament slugs to KNOWN_TOURNAMENTS.")


if __name__ == "__main__":
    main()
