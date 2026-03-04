#!/usr/bin/env python3
"""
Fetch Spreewölfe Berlin match schedules from spreewoelfe.de and generate iCal files.

This is a community project and is NOT affiliated with Spreewölfe Berlin e.V.
Schedule data is scraped from the publicly available website.

Usage:
    pip install requests beautifulsoup4
    python fetch_schedules.py

    # Fetch only a specific team:
    python fetch_schedules.py --team herren-i

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
from datetime import datetime, timezone
from urllib.parse import urljoin, unquote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Install them with:")
    print("  pip install requests beautifulsoup4")
    sys.exit(1)

BASE_URL = "https://www.spreewoelfe.de"
SPIELPLAENE_URL = f"{BASE_URL}/spielplaene/"

# Known team slugs from the website navigation.
# The script also auto-discovers teams from the Spielpläne page.
KNOWN_TEAMS = {
    "herren-i":    {"name": "Herren I",  "league": "Regionalliga Ost"},
    "herren-ii":   {"name": "Herren II", "league": "Landesliga"},
    "damen":       {"name": "Damen",     "league": "1. Damenbundesliga"},
    "jugend-u-16": {"name": "Jugend U-16", "league": "Jugendliga"},
    "schüler-u-13-1": {"name": "Schüler U-13", "league": "Schülerliga"},
    "bambini-u-10": {"name": "Bambini U-10", "league": "Bambiniliga"},
}


def fetch_page(url):
    """Fetch a page and return a BeautifulSoup object."""
    print(f"  Fetching {url} ...")
    resp = requests.get(url, timeout=30, headers={
        "User-Agent": "SpreewoelfeCalendarBot/1.0 (community project)"
    })
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def discover_teams():
    """
    Discover team schedule pages from the main Spielpläne page.
    Returns a dict of slug -> {name, url, league}.
    """
    print("Discovering teams from Spielpläne page...")
    soup = fetch_page(SPIELPLAENE_URL)
    teams = {}

    # Look for links under the Spielpläne navigation / page content
    # The website typically has sub-page links for each team
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Match links like /spielplaene/herren-i/ or /spielplaene/jugend-u-16/
        match = re.match(r"/spielplaene/([\w\-äöüÄÖÜ%]+)/?$", href)
        if not match:
            # Also try full URLs
            match = re.match(
                rf"{re.escape(BASE_URL)}/spielplaene/([\w\-äöüÄÖÜ%]+)/?$", href
            )
        if match:
            slug = unquote(match.group(1))
            name = link.get_text(strip=True)
            if not name:
                name = slug.replace("-", " ").title()

            known = KNOWN_TEAMS.get(slug, {})
            teams[slug] = {
                "name": known.get("name", name),
                "league": known.get("league", ""),
                "url": urljoin(BASE_URL, href),
                "slug": slug,
            }

    # Ensure known teams are included even if not found via links
    for slug, info in KNOWN_TEAMS.items():
        if slug not in teams:
            teams[slug] = {
                "name": info["name"],
                "league": info["league"],
                "url": f"{SPIELPLAENE_URL}{slug}/",
                "slug": slug,
            }

    print(f"  Found {len(teams)} teams: {', '.join(t['name'] for t in teams.values())}")
    return teams


def parse_schedule(soup, team_slug, team_name):
    """
    Parse a team schedule page and extract match events.
    Returns a list of event dicts.

    The spreewoelfe.de schedule pages typically contain a table or list
    with columns for date, time, home team, away team, and location.
    This function tries multiple parsing strategies.
    """
    events = []

    # Strategy 1: Look for HTML tables with match data
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            cell_texts = [c.get_text(strip=True) for c in cells]
            event = try_parse_table_row(cell_texts, team_slug, team_name)
            if event:
                events.append(event)

    # Strategy 2: Look for structured div/article elements
    if not events:
        # Some WordPress themes use div-based layouts
        for article in soup.find_all(["article", "div"], class_=re.compile(
            r"(spieltag|match|game|event|fixture)", re.I
        )):
            event = try_parse_block(article, team_slug, team_name)
            if event:
                events.append(event)

    # Strategy 3: Look for any date-like patterns in the content
    if not events:
        content = soup.find(["main", "article", "div"], class_=re.compile(
            r"(content|entry|post|page)", re.I
        ))
        if content:
            events = try_parse_freeform(content, team_slug, team_name)

    return events


def try_parse_table_row(cells, team_slug, team_name):
    """Try to parse a table row into a match event."""
    # Common patterns:
    # [date, time, home, guest, location, result]
    # [spieltag, date, time, home, guest, location]
    # [date, host, location]
    date_str = None
    time_str = None
    host = None
    location = None

    for cell in cells:
        # Try to find a date (DD.MM.YYYY or YYYY-MM-DD)
        if not date_str:
            dm = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", cell)
            if dm:
                date_str = f"{dm.group(3)}-{dm.group(2).zfill(2)}-{dm.group(1).zfill(2)}"
                continue
            dm = re.search(r"(\d{4})-(\d{2})-(\d{2})", cell)
            if dm:
                date_str = dm.group(0)
                continue

        # Try to find a time (HH:MM)
        if not time_str:
            tm = re.search(r"(\d{1,2}):(\d{2})", cell)
            if tm:
                time_str = f"{tm.group(1).zfill(2)}:{tm.group(2)}"
                continue

    if not date_str:
        return None

    if not time_str:
        time_str = "10:00"  # default to 10:00

    # The rest of the cells might be team names and location
    non_date_cells = []
    for cell in cells:
        if not re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", cell) and \
           not re.match(r"^\d{1,2}:\d{2}$", cell.strip()):
            non_date_cells.append(cell)

    if non_date_cells:
        host = non_date_cells[0] if non_date_cells else ""
        location = non_date_cells[-1] if len(non_date_cells) > 1 else ""

    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    uid_slug = team_slug.replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")

    return {
        "date": date_str,
        "time": time_str,
        "dt_start": dt.strftime("%Y%m%dT%H%M%S"),
        "dt_end": (dt.replace(hour=dt.hour + 3)).strftime("%Y%m%dT%H%M%S"),
        "host": host or "TBD",
        "location": location or "TBD",
        "summary": f"{team_name} Spieltag: {host or 'TBD'}",
        "uid": f"{uid_slug}-{dt.strftime('%Y%m%d')}@spreewolf.de",
    }


def try_parse_block(element, team_slug, team_name):
    """Try to parse a block element (div/article) into a match event."""
    text = element.get_text(" ", strip=True)
    dm = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if not dm:
        return None

    date_str = f"{dm.group(3)}-{dm.group(2).zfill(2)}-{dm.group(1).zfill(2)}"
    tm = re.search(r"(\d{1,2}):(\d{2})", text)
    time_str = f"{tm.group(1).zfill(2)}:{tm.group(2)}" if tm else "10:00"

    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    uid_slug = team_slug.replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")

    return {
        "date": date_str,
        "time": time_str,
        "dt_start": dt.strftime("%Y%m%dT%H%M%S"),
        "dt_end": (dt.replace(hour=dt.hour + 3)).strftime("%Y%m%dT%H%M%S"),
        "host": "TBD",
        "location": "TBD",
        "summary": f"{team_name} Spieltag",
        "uid": f"{uid_slug}-{dt.strftime('%Y%m%d')}@spreewolf.de",
    }


def try_parse_freeform(content, team_slug, team_name):
    """Try to extract match dates from free-form content."""
    events = []
    text = content.get_text("\n", strip=True)

    # Find all date patterns
    for dm in re.finditer(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text):
        date_str = f"{dm.group(3)}-{dm.group(2).zfill(2)}-{dm.group(1).zfill(2)}"

        # Look for a time near this date
        context = text[max(0, dm.start() - 50):dm.end() + 50]
        tm = re.search(r"(\d{1,2}):(\d{2})", context)
        time_str = f"{tm.group(1).zfill(2)}:{tm.group(2)}" if tm else "10:00"

        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        uid_slug = team_slug.replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")

        events.append({
            "date": date_str,
            "time": time_str,
            "dt_start": dt.strftime("%Y%m%dT%H%M%S"),
            "dt_end": (dt.replace(hour=dt.hour + 3)).strftime("%Y%m%dT%H%M%S"),
            "host": "TBD",
            "location": "TBD",
            "summary": f"{team_name} Spieltag",
            "uid": f"{uid_slug}-{dt.strftime('%Y%m%d')}@spreewolf.de",
        })

    return events


def generate_ical(events, team_name, team_slug):
    """Generate iCalendar content from a list of events."""
    uid_slug = team_slug.replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//Spreewolf {team_name} Plan//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
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
            f"DESCRIPTION:Gastgeber: {event['host']}",
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
        data = {"venues": [], "last_updated": "", "source": SPIELPLAENE_URL, "notes": ""}

    existing_addresses = {v["address"] for v in data["venues"]}

    for event in events:
        addr = event.get("location", "")
        if addr and addr != "TBD" and addr not in existing_addresses:
            data["venues"].append({
                "name": "",
                "team_home": event.get("host", ""),
                "address": addr,
                "notes": "auto-discovered",
            })
            existing_addresses.add(addr)

    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    with open(locations_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Locations database updated: {len(data['venues'])} venues")


def fetch_team_schedule(team, year):
    """Fetch and parse schedule for a single team."""
    url = team["url"]
    slug = team["slug"]
    name = team["name"]

    print(f"\nProcessing {name} ({slug})...")
    try:
        soup = fetch_page(url)
    except requests.RequestException as e:
        print(f"  ERROR: Could not fetch {url}: {e}")
        return []

    events = parse_schedule(soup, slug, name)

    # Filter to requested year
    events = [e for e in events if e["date"].startswith(str(year))]

    print(f"  Found {len(events)} events for {year}")
    return events


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Spreewölfe Berlin schedules and generate iCal files."
    )
    parser.add_argument(
        "--team",
        help="Fetch only a specific team by slug (e.g. herren-i, damen, jugend-u-16)",
    )
    parser.add_argument(
        "--year", type=int, default=datetime.now().year,
        help="Season year to filter events (default: current year)",
    )
    parser.add_argument(
        "--output", default=".",
        help="Output directory for generated files (default: current directory)",
    )
    parser.add_argument(
        "--skip-discover", action="store_true",
        help="Skip auto-discovery; use only known team slugs",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    locations_file = os.path.join(args.output, "locations.json")

    # Discover or use known teams
    if args.skip_discover:
        teams = {}
        for slug, info in KNOWN_TEAMS.items():
            teams[slug] = {
                "name": info["name"],
                "league": info["league"],
                "url": f"{SPIELPLAENE_URL}{slug}/",
                "slug": slug,
            }
    else:
        try:
            teams = discover_teams()
        except requests.RequestException as e:
            print(f"Could not discover teams: {e}")
            print("Falling back to known team list...")
            teams = {}
            for slug, info in KNOWN_TEAMS.items():
                teams[slug] = {
                    "name": info["name"],
                    "league": info["league"],
                    "url": f"{SPIELPLAENE_URL}{slug}/",
                    "slug": slug,
                }

    # Filter to specific team if requested
    if args.team:
        if args.team in teams:
            teams = {args.team: teams[args.team]}
        else:
            print(f"Unknown team: {args.team}")
            print(f"Available: {', '.join(teams.keys())}")
            sys.exit(1)

    # Fetch and generate for each team
    all_events = []
    generated_files = []
    for slug, team in teams.items():
        events = fetch_team_schedule(team, args.year)
        if events:
            ical_content = generate_ical(events, team["name"], slug)
            filename = f"{args.year}-{slug.replace('ü', 'ue').replace('ä', 'ae').replace('ö', 'oe')}.ics"
            filepath = os.path.join(args.output, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(ical_content)
            print(f"  Written: {filepath}")
            generated_files.append(filename)
            all_events.extend(events)
        else:
            print(f"  No events found for {team['name']} in {args.year}")

    # Update locations database
    if all_events:
        update_locations(all_events, locations_file)

    # Summary
    print("\n" + "=" * 60)
    print(f"Done! Generated {len(generated_files)} iCal files with {len(all_events)} total events.")
    if generated_files:
        print("Files:")
        for f in generated_files:
            print(f"  - {f}")
    else:
        print("No schedule data found. The website structure may have changed.")
        print("Check https://www.spreewoelfe.de/spielplaene/ manually and")
        print("update the parsing logic in this script if needed.")


if __name__ == "__main__":
    main()
