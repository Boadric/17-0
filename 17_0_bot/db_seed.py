import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import nflreadpy as nfl
import pandas as pd

try:
    from config import DB_PATH, NFL_TEAMS, get_canonical_team
except (ImportError, ValueError):
    from .config import DB_PATH, NFL_TEAMS, get_canonical_team

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Creates SQLite tables and ensures WAL mode is enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            college TEXT,
            draft_year INTEGER,
            draft_round INTEGER,
            draft_pick INTEGER,
            headshot_url TEXT,
            espn_id TEXT
        );

        CREATE TABLE IF NOT EXISTS player_seasons (
            player_id TEXT,
            season INTEGER,
            team TEXT,
            position TEXT, -- 'QB', 'RB', 'WR', 'TE'
            games_played INTEGER,
            ppr_fppg REAL, -- (Total PPR Fantasy Points / Games Played)
            PRIMARY KEY (player_id, season, team),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        );

        CREATE TABLE IF NOT EXISTS player_career_teams (
            player_id TEXT,
            team TEXT,
            season INTEGER,
            PRIMARY KEY (player_id, team, season)
        );

        CREATE TABLE IF NOT EXISTS special_connections (
            player_id_1 TEXT,
            player_id_2 TEXT,
            connection_type TEXT, -- 'ELITE' (+1) or 'LEGENDARY' (+2)
            label TEXT,           -- e.g., 'Manning to Harrison Connection'
            PRIMARY KEY (player_id_1, player_id_2)
        );

        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            total_score REAL,
            projected_record TEXT,
            roster_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_player_seasons_lookup 
            ON player_seasons(team, season, position);

        CREATE INDEX IF NOT EXISTS idx_player_name 
            ON players(name COLLATE NOCASE);

        CREATE INDEX IF NOT EXISTS idx_career_teams_player 
            ON player_career_teams(player_id);

        CREATE INDEX IF NOT EXISTS idx_career_teams_season 
            ON player_career_teams(team, season);
        """)
    logger.info("Database schema initialized at %s with WAL mode enabled.", db_path)
    return conn


def calculate_fppg(row: pd.Series) -> float:
    """Calculates standard PPR FPPG from season stats."""
    games = row.get("games", 0)
    if not games or games <= 0 or pd.isna(games):
        return 0.0

    fppr = row.get("fantasy_points_ppr")
    if pd.notna(fppr):
        return round(float(fppr) / float(games), 2)

    pass_yds = float(row.get("passing_yards", 0) or 0)
    pass_tds = float(row.get("passing_tds", 0) or 0)
    ints = float(row.get("interceptions", 0) or 0)
    rush_yds = float(row.get("rushing_yards", 0) or 0)
    rush_tds = float(row.get("rushing_tds", 0) or 0)
    rec = float(row.get("receptions", 0) or 0)
    rec_yds = float(row.get("receiving_yards", 0) or 0)
    rec_tds = float(row.get("receiving_tds", 0) or 0)
    fum_lost = (
        float(row.get("rushing_fumbles_lost", 0) or 0)
        + float(row.get("receiving_fumbles_lost", 0) or 0)
        + float(row.get("sack_fumbles_lost", 0) or 0)
    )

    tot_pts = (
        pass_yds * 0.04
        + pass_tds * 4.0
        - ints * 2.0
        + rush_yds * 0.1
        + rush_tds * 6.0
        + rec * 1.0
        + rec_yds * 0.1
        + rec_tds * 6.0
        - fum_lost * 2.0
    )
    return round(tot_pts / float(games), 2)


def seed_data(start_year: int = 1999, end_year: int = 2025, db_path: str = DB_PATH):
    """Fetches historical NFL data using nflreadpy and populates SQLite database."""
    conn = init_db(db_path)
    years = list(range(start_year, end_year + 1))

    logger.info("Fetching global players dataset from nflreadpy...")
    try:
        players_df = nfl.load_players().to_pandas()
    except Exception as e:
        logger.warning("Could not fetch load_players: %s", e)
        players_df = pd.DataFrame()

    logger.info("Fetching draft picks dataset from nflreadpy...")
    try:
        draft_df = nfl.load_draft_picks().to_pandas()
    except Exception as e:
        logger.warning("Could not fetch load_draft_picks: %s", e)
        draft_df = pd.DataFrame()

    # Pre-process player metadata
    player_meta: Dict[str, dict] = {}
    if not players_df.empty:
        for _, row in players_df.iterrows():
            pid = str(row.get("gsis_id", "") or "").strip()
            if not pid or pid.lower() == "nan":
                continue
            name = str(row.get("display_name", "") or row.get("football_name", "")).strip()
            college = str(row.get("college_name", "") or "").strip()
            headshot = str(row.get("headshot", "") or "").strip()
            espn_id = str(row.get("espn_id", "") or "").strip()
            draft_year = row.get("draft_year")
            draft_round = row.get("draft_round")
            draft_pick = row.get("draft_pick")

            try:
                dy = int(draft_year) if pd.notna(draft_year) else None
            except (ValueError, TypeError):
                dy = None
            try:
                dr = int(draft_round) if pd.notna(draft_round) else None
            except (ValueError, TypeError):
                dr = None
            try:
                dp = int(draft_pick) if pd.notna(draft_pick) else None
            except (ValueError, TypeError):
                dp = None

            player_meta[pid] = {
                "name": name,
                "college": college if college and college.lower() != "nan" else None,
                "headshot_url": headshot if headshot and headshot.lower() != "nan" else None,
                "espn_id": espn_id if espn_id and espn_id.lower() != "nan" else None,
                "draft_year": dy,
                "draft_round": dr,
                "draft_pick": dp,
            }

    # Augment with draft_df if draft info is missing
    if not draft_df.empty:
        for _, row in draft_df.iterrows():
            pid = str(row.get("gsis_id", "") or "").strip()
            if not pid or pid.lower() == "nan":
                continue
            name = str(row.get("pfr_player_name", "")).strip()
            college = str(row.get("college", "") or "").strip()
            season = row.get("season")
            d_round = row.get("round")
            d_pick = row.get("pick")

            try:
                dy = int(season) if pd.notna(season) else None
            except (ValueError, TypeError):
                dy = None
            try:
                dr = int(d_round) if pd.notna(d_round) else None
            except (ValueError, TypeError):
                dr = None
            try:
                dp = int(d_pick) if pd.notna(d_pick) else None
            except (ValueError, TypeError):
                dp = None

            if pid not in player_meta:
                player_meta[pid] = {
                    "name": name,
                    "college": college if college and college.lower() != "nan" else None,
                    "headshot_url": None,
                    "espn_id": None,
                    "draft_year": dy,
                    "draft_round": dr,
                    "draft_pick": dp,
                }
            else:
                if not player_meta[pid]["draft_year"] and dy:
                    player_meta[pid]["draft_year"] = dy
                if not player_meta[pid]["draft_round"] and dr:
                    player_meta[pid]["draft_round"] = dr
                if not player_meta[pid]["draft_pick"] and dp:
                    player_meta[pid]["draft_pick"] = dp
                if not player_meta[pid]["college"] and college and college.lower() != "nan":
                    player_meta[pid]["college"] = college

    logger.info("Loaded metadata for %d players.", len(player_meta))

    # Ingest seasonal rosters and stats year by year
    for yr in years:
        logger.info("--- Processing NFL Season %d ---", yr)
        try:
            rosters_yr = nfl.load_rosters([yr]).to_pandas()
        except Exception as e:
            logger.warning("Failed to fetch rosters for season %d: %s", yr, e)
            rosters_yr = pd.DataFrame()

        try:
            stats_yr = nfl.load_player_stats([yr]).to_pandas()
        except Exception as e:
            logger.warning("Failed to fetch seasonal stats for season %d: %s", yr, e)
            stats_yr = pd.DataFrame()

        if rosters_yr.empty and stats_yr.empty:
            logger.info("Skipping season %d (no data found)", yr)
            continue

        if not rosters_yr.empty:
            rosters_yr["canon_team"] = rosters_yr["team"].apply(get_canonical_team)

            career_records = []
            for _, r in rosters_yr.iterrows():
                pid = str(r.get("player_id", "") or "").strip()
                t = r.get("canon_team", "")
                if pid and t and pid.lower() != "nan":
                    career_records.append((pid, t, yr))

            with conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO player_career_teams (player_id, team, season) VALUES (?, ?, ?)",
                    career_records,
                )

            rosters_skill = rosters_yr[rosters_yr["position"].isin(["QB", "RB", "WR", "TE"])].copy()
        else:
            rosters_skill = pd.DataFrame()

        stats_dict: Dict[str, Tuple[int, float]] = {}
        if not stats_yr.empty:
            for _, srow in stats_yr.iterrows():
                pid = str(srow.get("player_id", "") or "").strip()
                if not pid or pid.lower() == "nan":
                    continue
                games = int(srow.get("games", 0) or 0)
                fppg = calculate_fppg(srow)
                stats_dict[pid] = (games, fppg)

        players_to_insert = []
        seasons_to_insert = []

        if not rosters_skill.empty:
            for _, rrow in rosters_skill.iterrows():
                pid = str(rrow.get("player_id", "") or "").strip()
                if not pid or pid.lower() == "nan":
                    continue
                name = str(rrow.get("player_name", "") or "").strip()
                pos = str(rrow.get("position", "")).strip().upper()
                team = rrow.get("canon_team", "")
                college = str(rrow.get("college", "") or "").strip()
                entry_yr = rrow.get("entry_year")
                try:
                    ey = int(entry_yr) if pd.notna(entry_yr) else None
                except (ValueError, TypeError):
                    ey = None

                if pid not in player_meta:
                    player_meta[pid] = {
                        "name": name,
                        "college": college if college and college.lower() != "nan" else None,
                        "headshot_url": None,
                        "espn_id": None,
                        "draft_year": ey,
                        "draft_round": None,
                        "draft_pick": None,
                    }
                else:
                    if not player_meta[pid]["name"] and name:
                        player_meta[pid]["name"] = name
                    if not player_meta[pid]["college"] and college and college.lower() != "nan":
                        player_meta[pid]["college"] = college
                    if not player_meta[pid]["draft_year"] and ey:
                        player_meta[pid]["draft_year"] = ey

                meta = player_meta[pid]
                players_to_insert.append((
                    pid,
                    meta["name"] or name,
                    meta["college"],
                    meta["draft_year"],
                    meta["draft_round"],
                    meta["draft_pick"],
                    meta["headshot_url"],
                    meta["espn_id"],
                ))

                games, fppg = stats_dict.get(pid, (0, 0.0))
                seasons_to_insert.append((pid, yr, team, pos, games, fppg))

        with conn:
            conn.executemany(
                """
                INSERT INTO players (player_id, name, college, draft_year, draft_round, draft_pick, headshot_url, espn_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id) DO UPDATE SET
                    name=coalesce(excluded.name, players.name),
                    college=coalesce(excluded.college, players.college),
                    draft_year=coalesce(excluded.draft_year, players.draft_year),
                    draft_round=coalesce(excluded.draft_round, players.draft_round),
                    draft_pick=coalesce(excluded.draft_pick, players.draft_pick),
                    headshot_url=coalesce(excluded.headshot_url, players.headshot_url),
                    espn_id=coalesce(excluded.espn_id, players.espn_id)
                """,
                players_to_insert,
            )
            conn.executemany(
                """
                INSERT INTO player_seasons (player_id, season, team, position, games_played, ppr_fppg)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id, season, team) DO UPDATE SET
                    position=excluded.position,
                    games_played=excluded.games_played,
                    ppr_fppg=excluded.ppr_fppg
                """,
                seasons_to_insert,
            )

        logger.info(
            "Season %d: Inserted %d player records and %d seasonal stat lines.",
            yr,
            len(players_to_insert),
            len(seasons_to_insert),
        )

    seed_special_connections(conn)
    conn.close()
    logger.info("Database seeding complete!")


def seed_special_connections(conn: sqlite3.Connection):
    """Populates iconic NFL special connections."""
    cur = conn.cursor()

    ICONIC_CONNECTIONS: List[Tuple[str, str, str, str]] = [
        ("Tom Brady", "Rob Gronkowski", "LEGENDARY", "Brady to Gronk"),
        ("Peyton Manning", "Marvin Harrison", "LEGENDARY", "Manning to Harrison"),
        ("Patrick Mahomes", "Travis Kelce", "LEGENDARY", "Mahomes to Kelce"),
        ("Patrick Mahomes", "Tyreek Hill", "LEGENDARY", "Mahomes to Hill"),
        ("Aaron Rodgers", "Davante Adams", "LEGENDARY", "Rodgers to Adams"),
        ("Matthew Stafford", "Calvin Johnson", "LEGENDARY", "Stafford to Megatron"),
        ("Ben Roethlisberger", "Antonio Brown", "LEGENDARY", "Big Ben to AB"),
        ("Matt Ryan", "Julio Jones", "LEGENDARY", "Ryan to Julio"),
        ("Philip Rivers", "Antonio Gates", "LEGENDARY", "Rivers to Gates"),
        ("Drew Brees", "Jimmy Graham", "ELITE", "Brees to Graham"),
        ("Joe Burrow", "Ja'Marr Chase", "ELITE", "Burrow to Chase"),
        ("Kurt Warner", "Torry Holt", "ELITE", "Greatest Show on Turf"),
        ("Kurt Warner", "Isaac Bruce", "ELITE", "Greatest Show on Turf"),
        ("Peyton Manning", "Reggie Wayne", "ELITE", "Manning to Wayne"),
        ("Josh Allen", "Stefon Diggs", "ELITE", "Allen to Diggs"),
        ("Tony Romo", "Jason Witten", "ELITE", "Romo to Witten"),
        ("Donovan McNabb", "Terrell Owens", "ELITE", "McNabb to TO"),
        ("Dak Prescott", "CeeDee Lamb", "ELITE", "Prescott to Lamb"),
        ("Tua Tagovailoa", "Tyreek Hill", "ELITE", "Tua to Hill"),
        ("Jalen Hurts", "A.J. Brown", "ELITE", "Hurts to Brown"),
        ("Eli Manning", "Odell Beckham", "ELITE", "Eli to OBJ"),
        ("Kirk Cousins", "Justin Jefferson", "ELITE", "Cousins to Jefferson"),
        ("Jared Goff", "Amon-Ra St. Brown", "ELITE", "Goff to Sun God"),
        ("Brock Purdy", "Christian McCaffrey", "ELITE", "Purdy to CMC"),
        ("Brock Purdy", "George Kittle", "ELITE", "Purdy to Kittle"),
        ("Lamar Jackson", "Mark Andrews", "ELITE", "Lamar to Andrews"),
        ("C.J. Stroud", "Nico Collins", "ELITE", "Stroud to Collins"),
    ]

    records = []
    for name1, name2, ctype, label in ICONIC_CONNECTIONS:
        cur.execute("SELECT player_id, name FROM players WHERE name LIKE ? ORDER BY LENGTH(name) ASC LIMIT 1", (f"%{name1}%",))
        r1 = cur.fetchone()
        cur.execute("SELECT player_id, name FROM players WHERE name LIKE ? ORDER BY LENGTH(name) ASC LIMIT 1", (f"%{name2}%",))
        r2 = cur.fetchone()

        if r1 and r2:
            pid1, pid2 = r1[0], r2[0]
            if pid1 > pid2:
                pid1, pid2 = pid2, pid1
            records.append((pid1, pid2, ctype, label))
            logger.info("Found connection: %s (%s) & %s (%s) -> [%s] %s", r1[1], pid1, r2[1], pid2, ctype, label)
        else:
            logger.warning("Could not find matching players for connection: %s and %s", name1, name2)

    with conn:
        conn.executemany(
            """
            INSERT INTO special_connections (player_id_1, player_id_2, connection_type, label)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id_1, player_id_2) DO UPDATE SET
                connection_type=excluded.connection_type,
                label=excluded.label
            """,
            records,
        )
    logger.info("Seeded %d special connections.", len(records))


if __name__ == "__main__":
    seed_data()
