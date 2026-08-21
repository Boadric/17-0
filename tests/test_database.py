import os
import sys
import sqlite3
from pathlib import Path

# Add 17_0_bot directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "17_0_bot"))

import pytest
import pytest_asyncio
from config import NFL_TEAMS
from database import (
    get_career_teammates_map,
    get_leaderboard,
    get_player_by_name_and_team,
    get_player_career_teams,
    get_random_season_for_team,
    get_random_team_for_season,
    get_random_team_season,
    get_special_connections_for_players,
    save_to_leaderboard,
    search_players_on_team,
)
from db_seed import init_db
from utils.scoring import RosterPlayer


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_game_data.db")
    conn = init_db(db_file)
    with conn:
        # Seed test players
        conn.executemany(
            """
            INSERT INTO players (player_id, name, college, draft_year, draft_round, draft_pick)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("P_TB12", "Tom Brady", "Michigan", 2000, 6, 199),
                ("P_GRONK", "Rob Gronkowski", "Arizona", 2010, 2, 42),
                ("P_MAHOMES", "Patrick Mahomes", "Texas Tech", 2017, 1, 10),
                ("P_KELCE", "Travis Kelce", "Cincinnati", 2013, 3, 63),
                ("P_HILL", "Tyreek Hill", "West Alabama", 2016, 5, 165),
            ],
        )
        # Seed test player seasons
        conn.executemany(
            """
            INSERT INTO player_seasons (player_id, season, team, position, games_played, ppr_fppg)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("P_TB12", 2020, "TB", "QB", 16, 21.1),
                ("P_GRONK", 2020, "TB", "TE", 16, 10.2),
                ("P_MAHOMES", 2018, "KC", "QB", 16, 28.9),
                ("P_KELCE", 2018, "KC", "TE", 16, 18.5),
                ("P_HILL", 2018, "KC", "WR", 16, 20.9),
            ],
        )
        # Seed career teams
        conn.executemany(
            """
            INSERT INTO player_career_teams (player_id, team, season)
            VALUES (?, ?, ?)
            """,
            [
                ("P_TB12", "NE", 2018),
                ("P_GRONK", "NE", 2018),
                ("P_TB12", "TB", 2020),
                ("P_GRONK", "TB", 2020),
                ("P_MAHOMES", "KC", 2018),
                ("P_KELCE", "KC", 2018),
                ("P_HILL", "KC", 2018),
            ],
        )
        # Seed special connections
        conn.executemany(
            """
            INSERT INTO special_connections (player_id_1, player_id_2, connection_type, label)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("P_GRONK", "P_TB12", "LEGENDARY", "Brady to Gronk"),
                ("P_KELCE", "P_MAHOMES", "LEGENDARY", "Mahomes to Kelce"),
            ],
        )
    conn.close()
    return db_file


@pytest.mark.asyncio
async def test_get_random_team_season(temp_db):
    team, season = await get_random_team_season(temp_db)
    assert team in ["TB", "KC"]
    assert season in [2018, 2020]


@pytest.mark.asyncio
async def test_search_and_get_player(temp_db):
    # Search players on 2018 KC
    players = await search_players_on_team("KC", 2018, db_path=temp_db)
    assert len(players) == 3
    assert players[0]["name"] == "Patrick Mahomes"

    # Search with partial match
    mahomes = await get_player_by_name_and_team("mahomes", "KC", 2018, db_path=temp_db)
    assert mahomes is not None
    assert mahomes["name"] == "Patrick Mahomes"
    assert mahomes["position"] == "QB"

    # Search for nonexistent player
    fake = await get_player_by_name_and_team("Peyton Manning", "KC", 2018, db_path=temp_db)
    assert fake is None


@pytest.mark.asyncio
async def test_career_teammates_and_special_connections(temp_db):
    # Check career teammates between Brady & Gronk
    teammates = await get_career_teammates_map(["P_TB12", "P_GRONK"], db_path=temp_db)
    assert len(teammates) == 1

    # Check special connections
    conn_map = await get_special_connections_for_players(["P_TB12", "P_GRONK"], db_path=temp_db)
    assert len(conn_map) == 1
    key = tuple(sorted(["P_TB12", "P_GRONK"]))
    assert conn_map[key][0] == "LEGENDARY"


@pytest.mark.asyncio
async def test_leaderboard_flow(temp_db):
    roster = {
        "QB": RosterPlayer("P1", "Test QB", "QB", "QB", "KC", 2018, 25.0),
        "TE": RosterPlayer("P2", "Test TE", "TE", "TE", "KC", 2018, 15.0),
    }
    saved_id = await save_to_leaderboard(
        user_id="12345",
        username="Tester",
        total_score=162.5,
        projected_record="17-0",
        roster=roster,
        db_path=temp_db,
    )
    assert saved_id > 0

    entries = await get_leaderboard(limit=5, db_path=temp_db)
    assert len(entries) == 1
    assert entries[0]["username"] == "Tester"
    assert entries[0]["total_score"] == 162.5
    assert entries[0]["projected_record"] == "17-0"
    assert "QB" in entries[0]["roster"]
