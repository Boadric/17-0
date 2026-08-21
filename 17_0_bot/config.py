import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH") or str(BASE_DIR / "game_data.db")

# Discord Bot Credentials
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or ""
APPLICATION_ID = os.getenv("APPLICATION_ID") or "1540222119697322004"
PUBLIC_KEY = os.getenv("PUBLIC_KEY") or "ba6816adaa9ecefb3e05aea8218d7fcb9ac1893a4845df3f3832082eae4a069c"
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID")) if os.getenv("DISCORD_GUILD_ID") else None

# Game Constants
TOTAL_ROUNDS = 7
SEASONS_RANGE = (1999, 2024)  # Historical seasons available

# Roster Slots and Position Eligibility
ROSTER_SLOTS = ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLX"]

SLOT_ELIGIBILITY = {
    "QB": ["QB"],
    "RB1": ["RB"],
    "RB2": ["RB"],
    "WR1": ["WR"],
    "WR2": ["WR"],
    "TE": ["TE"],
    "FLX": ["RB", "WR", "TE"],
}

POSITION_TO_SLOTS = {
    "QB": ["QB"],
    "RB": ["RB1", "RB2", "FLX"],
    "WR": ["WR1", "WR2", "FLX"],
    "TE": ["TE", "FLX"],
}

# NFL Franchise Canonical Info, Aliases, Colors and Emojis
NFL_TEAMS = {
    "ARI": {
        "name": "Arizona Cardinals",
        "city": "Arizona",
        "mascot": "Cardinals",
        "aliases": ["ARI", "ARZ"],
        "color": 0x97233F,
        "emoji": "🦩",
    },
    "ATL": {
        "name": "Atlanta Falcons",
        "city": "Atlanta",
        "mascot": "Falcons",
        "aliases": ["ATL"],
        "color": 0xA71930,
        "emoji": "🦅",
    },
    "BAL": {
        "name": "Baltimore Ravens",
        "city": "Baltimore",
        "mascot": "Ravens",
        "aliases": ["BAL", "BLT"],
        "color": 0x241773,
        "emoji": "🐦‍⬛",
    },
    "BUF": {
        "name": "Buffalo Bills",
        "city": "Buffalo",
        "mascot": "Bills",
        "aliases": ["BUF"],
        "color": 0x00338D,
        "emoji": "🦬",
    },
    "CAR": {
        "name": "Carolina Panthers",
        "city": "Carolina",
        "mascot": "Panthers",
        "aliases": ["CAR"],
        "color": 0x0085CA,
        "emoji": "🐆",
    },
    "CHI": {
        "name": "Chicago Bears",
        "city": "Chicago",
        "mascot": "Bears",
        "aliases": ["CHI"],
        "color": 0x0B162A,
        "emoji": "🐻",
    },
    "CIN": {
        "name": "Cincinnati Bengals",
        "city": "Cincinnati",
        "mascot": "Bengals",
        "aliases": ["CIN"],
        "color": 0xFB4F14,
        "emoji": "🐅",
    },
    "CLE": {
        "name": "Cleveland Browns",
        "city": "Cleveland",
        "mascot": "Browns",
        "aliases": ["CLE", "CLV"],
        "color": 0x311D00,
        "emoji": "🐶",
    },
    "DAL": {
        "name": "Dallas Cowboys",
        "city": "Dallas",
        "mascot": "Cowboys",
        "aliases": ["DAL"],
        "color": 0x003594,
        "emoji": "⭐",
    },
    "DEN": {
        "name": "Denver Broncos",
        "city": "Denver",
        "mascot": "Broncos",
        "aliases": ["DEN"],
        "color": 0xFB4F14,
        "emoji": "🐴",
    },
    "DET": {
        "name": "Detroit Lions",
        "city": "Detroit",
        "mascot": "Lions",
        "aliases": ["DET"],
        "color": 0x0076B6,
        "emoji": "🦁",
    },
    "GB": {
        "name": "Green Bay Packers",
        "city": "Green Bay",
        "mascot": "Packers",
        "aliases": ["GB", "GBP"],
        "color": 0x203731,
        "emoji": "🧀",
    },
    "HOU": {
        "name": "Houston Texans",
        "city": "Houston",
        "mascot": "Texans",
        "aliases": ["HOU", "HST"],
        "color": 0x03202F,
        "emoji": "🐂",
    },
    "IND": {
        "name": "Indianapolis Colts",
        "city": "Indianapolis",
        "mascot": "Colts",
        "aliases": ["IND"],
        "color": 0x002C5F,
        "emoji": "🐎",
    },
    "JAX": {
        "name": "Jacksonville Jaguars",
        "city": "Jacksonville",
        "mascot": "Jaguars",
        "aliases": ["JAX", "JAC"],
        "color": 0x006778,
        "emoji": "🐆",
    },
    "KC": {
        "name": "Kansas City Chiefs",
        "city": "Kansas City",
        "mascot": "Chiefs",
        "aliases": ["KC", "KAN"],
        "color": 0xE31837,
        "emoji": "🏹",
    },
    "LV": {
        "name": "Las Vegas Raiders",
        "city": "Las Vegas",
        "mascot": "Raiders",
        "aliases": ["LV", "OAK", "RAI", "LVR"],
        "color": 0x000000,
        "emoji": "☠️",
    },
    "LAC": {
        "name": "Los Angeles Chargers",
        "city": "Los Angeles",
        "mascot": "Chargers",
        "aliases": ["LAC", "SD", "SDG"],
        "color": 0x0080C6,
        "emoji": "⚡",
    },
    "LAR": {
        "name": "Los Angeles Rams",
        "city": "Los Angeles",
        "mascot": "Rams",
        "aliases": ["LAR", "LA", "STL", "RAM"],
        "color": 0x003594,
        "emoji": "🐏",
    },
    "MIA": {
        "name": "Miami Dolphins",
        "city": "Miami",
        "mascot": "Dolphins",
        "aliases": ["MIA"],
        "color": 0x008E97,
        "emoji": "🐬",
    },
    "MIN": {
        "name": "Minnesota Vikings",
        "city": "Minnesota",
        "mascot": "Vikings",
        "aliases": ["MIN"],
        "color": 0x4F2683,
        "emoji": "🛡️",
    },
    "NE": {
        "name": "New England Patriots",
        "city": "New England",
        "mascot": "Patriots",
        "aliases": ["NE", "NWE"],
        "color": 0x002244,
        "emoji": "🇺🇸",
    },
    "NO": {
        "name": "New Orleans Saints",
        "city": "New Orleans",
        "mascot": "Saints",
        "aliases": ["NO", "NOR"],
        "color": 0xD3BC8D,
        "emoji": "⚜️",
    },
    "NYG": {
        "name": "New York Giants",
        "city": "New York",
        "mascot": "Giants",
        "aliases": ["NYG"],
        "color": 0x0B2265,
        "emoji": "🗽",
    },
    "NYJ": {
        "name": "New York Jets",
        "city": "New York",
        "mascot": "Jets",
        "aliases": ["NYJ"],
        "color": 0x125740,
        "emoji": "✈️",
    },
    "PHI": {
        "name": "Philadelphia Eagles",
        "city": "Philadelphia",
        "mascot": "Eagles",
        "aliases": ["PHI"],
        "color": 0x004C54,
        "emoji": "🦅",
    },
    "PIT": {
        "name": "Pittsburgh Steelers",
        "city": "Pittsburgh",
        "mascot": "Steelers",
        "aliases": ["PIT"],
        "color": 0xFFB612,
        "emoji": "🔩",
    },
    "SF": {
        "name": "San Francisco 49ers",
        "city": "San Francisco",
        "mascot": "49ers",
        "aliases": ["SF", "SFO"],
        "color": 0xAA0000,
        "emoji": "⛏️",
    },
    "SEA": {
        "name": "Seattle Seahawks",
        "city": "Seattle",
        "mascot": "Seahawks",
        "aliases": ["SEA"],
        "color": 0x002244,
        "emoji": "🌊",
    },
    "TB": {
        "name": "Tampa Bay Buccaneers",
        "city": "Tampa Bay",
        "mascot": "Buccaneers",
        "aliases": ["TB", "TAM"],
        "color": 0xD50A0A,
        "emoji": "🏴‍☠️",
    },
    "TEN": {
        "name": "Tennessee Titans",
        "city": "Tennessee",
        "mascot": "Titans",
        "aliases": ["TEN", "OTI"],
        "color": 0x0C2340,
        "emoji": "⚔️",
    },
    "WAS": {
        "name": "Washington Commanders",
        "city": "Washington",
        "mascot": "Commanders",
        "aliases": ["WAS", "WSH"],
        "color": 0x5A1414,
        "emoji": "🪖",
    },
}

# Reverse lookup dictionary: maps any alias to canonical code
ALIAS_TO_CANONICAL = {}
for canon, data in NFL_TEAMS.items():
    ALIAS_TO_CANONICAL[canon] = canon
    for alias in data.get("aliases", []):
        ALIAS_TO_CANONICAL[alias.upper()] = canon


def get_canonical_team(alias: str) -> str:
    """Returns canonical team code for any given alias."""
    if not alias:
        return ""
    alias_clean = alias.strip().upper()
    return ALIAS_TO_CANONICAL.get(alias_clean, alias_clean)


def get_team_display_name(team_code: str, season: int | None = None) -> str:
    """Returns the historically accurate or canonical franchise name."""
    canon = get_canonical_team(team_code)
    # Historic name handling for relocated/rebranded franchises
    if canon == "LAR" and season and season < 2016:
        return "St. Louis Rams"
    if canon == "LAC" and season and season < 2017:
        return "San Diego Chargers"
    if canon == "LV" and season and season < 2020:
        return "Oakland Raiders"
    if canon == "WAS" and season:
        if season <= 2019:
            return "Washington Redskins"
        elif season in (2020, 2021):
            return "Washington Football Team"
        else:
            return "Washington Commanders"
    if canon in NFL_TEAMS:
        return NFL_TEAMS[canon]["name"]
    return team_code
