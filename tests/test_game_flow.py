import os
import sys
from pathlib import Path

# Add 17_0_bot directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "17_0_bot"))

import pytest
from cogs.game import GameSession
from db_seed import init_db
from utils.scoring import RosterPlayer


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_flow.db")
    conn = init_db(db_file)
    with conn:
        conn.executemany(
            """
            INSERT INTO players (player_id, name, college, draft_year, draft_round, draft_pick)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("P1", "Quarterback 1", "College A", 2020, 1, 1),
                ("P2", "Runningback 1", "College B", 2020, 1, 2),
                ("P3", "Runningback 2", "College C", 2021, 2, 35),
                ("P4", "Wideout 1", "College A", 2020, 1, 15),
                ("P5", "Wideout 2", "College D", 2022, 2, 40),
                ("P6", "Tight End 1", "College E", 2019, 3, 75),
                ("P7", "Flex Receiver", "College B", 2021, 4, 105),
            ],
        )
        conn.executemany(
            """
            INSERT INTO player_seasons (player_id, season, team, position, games_played, ppr_fppg)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("P1", 2020, "KC", "QB", 16, 25.0),
                ("P2", 2020, "KC", "RB", 16, 18.0),
                ("P3", 2021, "GB", "RB", 16, 16.0),
                ("P4", 2020, "KC", "WR", 16, 20.0),
                ("P5", 2022, "BUF", "WR", 16, 19.0),
                ("P6", 2019, "SF", "TE", 16, 15.0),
                ("P7", 2021, "MIN", "WR", 16, 17.0),
            ],
        )
    conn.close()
    return db_file


@pytest.mark.asyncio
async def test_game_session_initialization(temp_db):
    session = GameSession(user_id=123, username="PlayerOne", channel_id=456, db_path=temp_db)
    assert session.round_num == 1
    assert session.team_rerolls_left == 1
    assert session.year_rerolls_left == 1
    assert len(session.roster) == 0

    # Test open slots
    assert session.get_open_slots_for_position("QB") == ["QB"]
    assert session.get_open_slots_for_position("RB") == ["RB1", "RB2", "FLX"]
    assert session.get_open_slots_for_position("WR") == ["WR1", "WR2", "FLX"]
    assert session.get_open_slots_for_position("TE") == ["TE", "FLX"]


@pytest.mark.asyncio
async def test_game_session_roster_filling(temp_db):
    session = GameSession(user_id=123, username="PlayerOne", channel_id=456, db_path=temp_db)

    # Add QB
    session.roster["QB"] = RosterPlayer("P1", "QB 1", "QB", "QB", "KC", 2020, 25.0)
    assert session.get_open_slots_for_position("QB") == []

    # Add RB1, RB2
    session.roster["RB1"] = RosterPlayer("P2", "RB 1", "RB", "RB1", "KC", 2020, 18.0)
    session.roster["RB2"] = RosterPlayer("P3", "RB 2", "RB", "RB2", "GB", 2021, 16.0)
    assert session.get_open_slots_for_position("RB") == ["FLX"]

    # Add WR1, WR2, TE, FLX
    session.roster["WR1"] = RosterPlayer("P4", "WR 1", "WR", "WR1", "KC", 2020, 20.0)
    session.roster["WR2"] = RosterPlayer("P5", "WR 2", "WR", "WR2", "BUF", 2022, 19.0)
    session.roster["TE"] = RosterPlayer("P6", "TE 1", "TE", "TE", "SF", 2019, 15.0)
    session.roster["FLX"] = RosterPlayer("P7", "WR 3", "WR", "FLX", "MIN", 2021, 17.0)

    # Roster is full (7/7)
    assert len(session.roster) == 7
    assert session.get_open_slots_for_position("RB") == []
    assert session.get_open_slots_for_position("WR") == []
    assert session.get_open_slots_for_position("TE") == []

    breakdown = await session.recalculate_score()
    assert breakdown.base_fppg == (25.0 + 18.0 + 16.0 + 20.0 + 19.0 + 15.0 + 17.0)
    assert breakdown.total_score >= breakdown.base_fppg

    # Test embed building
    embed = session.build_active_embed()
    field_names = [f.name for f in embed.fields]
    assert any("Available Weapons" in name for name in field_names)
    assert any("Active Fantasy Roster" in name for name in field_names)
    assert any("Team Projection" in name for name in field_names)

    over_embed = session.build_game_over_embed()
    assert "Game Complete" in over_embed.title
