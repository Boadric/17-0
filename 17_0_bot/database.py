import contextlib
import json
import random
from typing import Any, Dict, List, Optional, Set, Tuple
import aiosqlite

try:
    from config import DB_PATH, NFL_TEAMS, get_canonical_team
    from utils.scoring import RosterPlayer
except (ImportError, ValueError):
    from .config import DB_PATH, NFL_TEAMS, get_canonical_team
    from .utils.scoring import RosterPlayer


@contextlib.asynccontextmanager
async def get_db(db_path: str = DB_PATH):
    """Opens a non-blocking aiosqlite connection with WAL mode enabled."""
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def get_random_team_season(db_path: str = DB_PATH) -> Tuple[str, int]:
    """Rolls a random (team, season) tuple with available skill position players."""
    async with get_db(db_path) as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT team, season 
            FROM player_seasons 
            WHERE position IN ('QB', 'RB', 'WR', 'TE')
            """
        )
        rows = await cursor.fetchall()
        if not rows:
            teams = list(NFL_TEAMS.keys())
            return random.choice(teams), random.randint(1999, 2024)
        selected = random.choice(rows)
        return selected["team"], selected["season"]


async def get_random_team_for_season(season: int, current_team: Optional[str] = None, db_path: str = DB_PATH) -> str:
    """Rerolls the team for a specific season."""
    async with get_db(db_path) as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT team 
            FROM player_seasons 
            WHERE season = ? AND position IN ('QB', 'RB', 'WR', 'TE')
            """,
            (season,),
        )
        rows = await cursor.fetchall()
        teams = [r["team"] for r in rows if r["team"] != current_team]
        if teams:
            return random.choice(teams)
        all_teams = [t for t in NFL_TEAMS.keys() if t != current_team]
        return random.choice(all_teams) if all_teams else (current_team or "KC")


async def get_random_season_for_team(team: str, current_season: Optional[int] = None, db_path: str = DB_PATH) -> int:
    """Rerolls the season for a specific franchise."""
    canon_team = get_canonical_team(team)
    async with get_db(db_path) as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT season 
            FROM player_seasons 
            WHERE team = ? AND position IN ('QB', 'RB', 'WR', 'TE')
            """,
            (canon_team,),
        )
        rows = await cursor.fetchall()
        seasons = [r["season"] for r in rows if r["season"] != current_season]
        if seasons:
            return random.choice(seasons)
        all_seasons = [s for s in range(1999, 2025) if s != current_season]
        return random.choice(all_seasons) if all_seasons else (current_season or 2020)


async def search_players_on_team(
    team: str,
    season: int,
    query: Optional[str] = None,
    positions: Optional[List[str]] = None,
    position_filter: Optional[str] = None,
    limit: int = 25,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    """
    Searches for offensive players on a specific team and season.
    Filters strictly by eligible positions.
    """
    canon_team = get_canonical_team(team)
    async with get_db(db_path) as db:
        conditions = ["ps.team = ?", "ps.season = ?"]
        params: List[Any] = [canon_team, season]

        # Support both position_filter (single) and positions (list of eligible)
        if position_filter and position_filter.upper() in ("QB", "RB", "WR", "TE"):
            conditions.append("ps.position = ?")
            params.append(position_filter.upper())
        elif positions is not None:
            clean_positions = [p.upper() for p in positions if p.upper() in ("QB", "RB", "WR", "TE")]
            if clean_positions:
                placeholders = ",".join("?" for _ in clean_positions)
                conditions.append(f"ps.position IN ({placeholders})")
                params.extend(clean_positions)
            else:
                conditions.append("1=0")  # No eligible positions
        else:
            conditions.append("ps.position IN ('QB', 'RB', 'WR', 'TE')")

        if query:
            clean_q = f"%{query.strip()}%"
            conditions.append("p.name LIKE ?")
            params.append(clean_q)

        where_clause = " AND ".join(conditions)
        sql = f"""
        SELECT 
            p.player_id, p.name, p.college, p.draft_year, p.draft_round, p.draft_pick,
            ps.season, ps.team, ps.position, ps.games_played, ps.ppr_fppg
        FROM player_seasons ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE {where_clause}
        ORDER BY ps.ppr_fppg DESC, ps.games_played DESC
        LIMIT ?
        """
        params.append(limit)
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_player_by_id_and_team(
    player_id: str,
    team: str,
    season: int,
    db_path: str = DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Fetches full player details for a specific player_id on a team/season."""
    canon_team = get_canonical_team(team)
    async with get_db(db_path) as db:
        sql = """
        SELECT 
            p.player_id, p.name, p.college, p.draft_year, p.draft_round, p.draft_pick,
            ps.season, ps.team, ps.position, ps.games_played, ps.ppr_fppg
        FROM player_seasons ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.player_id = ? AND ps.team = ? AND ps.season = ?
        LIMIT 1
        """
        cursor = await db.execute(sql, (player_id, canon_team, season))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_player_by_name_and_team(
    name_query: str,
    team: str,
    season: int,
    db_path: str = DB_PATH,
) -> Optional[Dict[str, Any]]:
    """
    Finds a single player on a team/season by exact or best-effort fuzzy match.
    """
    canon_team = get_canonical_team(team)
    clean_q = name_query.strip()
    if not clean_q:
        return None

    async with get_db(db_path) as db:
        # 1. Exact match
        sql_exact = """
        SELECT 
            p.player_id, p.name, p.college, p.draft_year, p.draft_round, p.draft_pick,
            ps.season, ps.team, ps.position, ps.games_played, ps.ppr_fppg
        FROM player_seasons ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.team = ? AND ps.season = ? AND ps.position IN ('QB', 'RB', 'WR', 'TE')
          AND LOWER(p.name) = LOWER(?)
        LIMIT 1
        """
        cursor = await db.execute(sql_exact, (canon_team, season, clean_q))
        row = await cursor.fetchone()
        if row:
            return dict(row)

        # 2. Starts-with match
        sql_starts = """
        SELECT 
            p.player_id, p.name, p.college, p.draft_year, p.draft_round, p.draft_pick,
            ps.season, ps.team, ps.position, ps.games_played, ps.ppr_fppg
        FROM player_seasons ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.team = ? AND ps.season = ? AND ps.position IN ('QB', 'RB', 'WR', 'TE')
          AND p.name LIKE ?
        ORDER BY ps.ppr_fppg DESC
        LIMIT 1
        """
        cursor = await db.execute(sql_starts, (canon_team, season, f"{clean_q}%"))
        row = await cursor.fetchone()
        if row:
            return dict(row)

        # 3. Substring match
        sql_sub = """
        SELECT 
            p.player_id, p.name, p.college, p.draft_year, p.draft_round, p.draft_pick,
            ps.season, ps.team, ps.position, ps.games_played, ps.ppr_fppg
        FROM player_seasons ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.team = ? AND ps.season = ? AND ps.position IN ('QB', 'RB', 'WR', 'TE')
          AND p.name LIKE ?
        ORDER BY ps.ppr_fppg DESC
        LIMIT 1
        """
        cursor = await db.execute(sql_sub, (canon_team, season, f"%{clean_q}%"))
        row = await cursor.fetchone()
        if row:
            return dict(row)

        return None


async def get_player_career_teams(player_id: str, db_path: str = DB_PATH) -> Set[str]:
    """Retrieves all franchise codes a player played for across their career."""
    async with get_db(db_path) as db:
        cursor = await db.execute(
            "SELECT DISTINCT team FROM player_career_teams WHERE player_id = ?",
            (player_id,),
        )
        rows = await cursor.fetchall()
        return {r["team"] for r in rows}


async def get_career_teammates_map(player_ids: List[str], db_path: str = DB_PATH) -> Set[Tuple[str, str]]:
    """
    Finds all pairs of player_ids that were ever teammates on the same NFL team in the same season.
    """
    if len(player_ids) < 2:
        return set()

    placeholders = ",".join("?" for _ in player_ids)
    sql = f"""
    SELECT DISTINCT p1.player_id AS id1, p2.player_id AS id2
    FROM player_career_teams p1
    JOIN player_career_teams p2 
      ON p1.team = p2.team AND p1.season = p2.season
    WHERE p1.player_id IN ({placeholders})
      AND p2.player_id IN ({placeholders})
      AND p1.player_id < p2.player_id
    """
    async with get_db(db_path) as db:
        cursor = await db.execute(sql, player_ids + player_ids)
        rows = await cursor.fetchall()
        return {(r["id1"], r["id2"]) for r in rows}


async def get_special_connections_for_players(
    player_ids: List[str], db_path: str = DB_PATH
) -> Dict[Tuple[str, str], Tuple[str, str]]:
    """
    Finds any Special Connections (ELITE / LEGENDARY) between player pairs.
    """
    if len(player_ids) < 2:
        return {}

    placeholders = ",".join("?" for _ in player_ids)
    sql = f"""
    SELECT player_id_1, player_id_2, connection_type, label
    FROM special_connections
    WHERE (player_id_1 IN ({placeholders}) AND player_id_2 IN ({placeholders}))
    """
    async with get_db(db_path) as db:
        cursor = await db.execute(sql, player_ids + player_ids)
        rows = await cursor.fetchall()
        connections = {}
        for r in rows:
            p1, p2 = r["player_id_1"], r["player_id_2"]
            key = (min(p1, p2), max(p1, p2))
            connections[key] = (r["connection_type"], r["label"])
        return connections


async def save_to_leaderboard(
    user_id: str,
    username: str,
    total_score: float,
    projected_record: str,
    roster: Dict[str, RosterPlayer],
    db_path: str = DB_PATH,
) -> int:
    """Saves a completed game to the leaderboard table."""
    roster_data = {}
    for slot, player in roster.items():
        roster_data[slot] = {
            "player_id": player.player_id,
            "name": player.name,
            "position": player.position,
            "drafted_team": player.drafted_team,
            "drafted_season": player.drafted_season,
            "base_fppg": player.base_fppg,
            "chemistry_fppg": player.chemistry_fppg,
            "total_fppg": player.total_fppg,
            "applied_bonuses": player.applied_bonuses,
        }

    roster_json = json.dumps(roster_data)

    async with get_db(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO leaderboard (user_id, username, total_score, projected_record, roster_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, username, total_score, projected_record, roster_json),
        )
        await db.commit()
        return cursor.lastrowid or 0


async def get_leaderboard(limit: int = 10, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Fetches top N highest-scoring entries from the leaderboard."""
    async with get_db(db_path) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, username, total_score, projected_record, roster_json, created_at
            FROM leaderboard
            ORDER BY total_score DESC, created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            entry = dict(r)
            try:
                entry["roster"] = json.loads(entry["roster_json"])
            except Exception:
                entry["roster"] = {}
            results.append(entry)
        return results
