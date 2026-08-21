import os
import sys
from pathlib import Path

# Add 17_0_bot directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "17_0_bot"))

import pytest
import pytest_asyncio
from config import DB_PATH
from database import (
    get_career_teammates_map,
    get_player_by_name_and_team,
    get_player_career_teams,
    get_random_season_for_team,
    get_random_team_for_season,
    get_random_team_season,
    get_special_connections_for_players,
    search_players_on_team,
)
from utils.scoring import RosterPlayer, calculate_chemistry


@pytest.mark.asyncio
async def test_real_db_rolls_and_searches():
    if not os.path.exists(DB_PATH):
        pytest.skip("game_data.db not present")

    team, season = await get_random_team_season()
    assert 1999 <= season <= 2024
    assert len(team) >= 2

    # Search players on 2018 KC
    kc_players = await search_players_on_team("KC", 2018, limit=10)
    assert len(kc_players) > 0
    names = [p["name"] for p in kc_players]
    assert any("Mahomes" in name for name in names)

    # Fuzzy find Brady in 2020 TB
    brady = await get_player_by_name_and_team("Brady", "TB", 2020)
    assert brady is not None
    assert brady["name"] == "Tom Brady"
    assert brady["position"] == "QB"
    assert brady["ppr_fppg"] > 20.0


@pytest.mark.asyncio
async def test_real_db_special_connections_brady_gronk():
    if not os.path.exists(DB_PATH):
        pytest.skip("game_data.db not present")

    brady = await get_player_by_name_and_team("Tom Brady", "TB", 2020)
    gronk = await get_player_by_name_and_team("Rob Gronkowski", "TB", 2020)

    assert brady is not None and gronk is not None

    p_brady = RosterPlayer(
        player_id=brady["player_id"],
        name=brady["name"],
        position="QB",
        slot="QB",
        drafted_team="TB",
        drafted_season=2020,
        base_fppg=brady["ppr_fppg"],
        college=brady.get("college"),
        draft_year=brady.get("draft_year"),
        career_teams=await get_player_career_teams(brady["player_id"]),
    )

    p_gronk = RosterPlayer(
        player_id=gronk["player_id"],
        name=gronk["name"],
        position="TE",
        slot="TE",
        drafted_team="TB",
        drafted_season=2020,
        base_fppg=gronk["ppr_fppg"],
        college=gronk.get("college"),
        draft_year=gronk.get("draft_year"),
        career_teams=await get_player_career_teams(gronk["player_id"]),
    )

    player_ids = [p_brady.player_id, p_gronk.player_id]
    conn_map = await get_special_connections_for_players(player_ids)
    teammates = await get_career_teammates_map(player_ids)

    roster = {"QB": p_brady, "TE": p_gronk}
    breakdown = calculate_chemistry(roster, special_connections=conn_map, career_teammates_map=teammates)

    # Both are 2020 TB (Same Team +4 team total) and Legendary (Brady to Gronk +4 team total) = +8.0 Chemistry
    assert breakdown.chemistry_fppg >= 8.0
    assert any(link.bonus_type == "LEGENDARY" for link in breakdown.active_links)
    assert any(link.bonus_type == "SAME_TEAM_SEASON" for link in breakdown.active_links)
