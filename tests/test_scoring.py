import os
import sys
from pathlib import Path

# Add 17_0_bot directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "17_0_bot"))

import pytest
from utils.scoring import (
    RosterPlayer,
    calculate_chemistry,
    project_season_record,
)


def test_project_season_record_tiers():
    assert project_season_record(165.0) == ("17-0", "Undefeated Champion", "🏆")
    assert project_season_record(160.0) == ("17-0", "Undefeated Champion", "🏆")

    assert project_season_record(155.0) == ("16-1", "Super Bowl Contender", "💍")
    assert project_season_record(148.0) == ("15-2", "Super Bowl Contender", "💍")

    assert project_season_record(142.0) == ("14-3", "Playoff Lock", "🔒")
    assert project_season_record(136.0) == ("13-4", "Playoff Lock", "🔒")
    assert project_season_record(131.0) == ("12-5", "Playoff Lock", "🔒")

    assert project_season_record(126.0) == ("11-6", "Wild Card Bubble", "🫧")
    assert project_season_record(121.0) == ("10-7", "Wild Card Bubble", "🫧")
    assert project_season_record(116.0) == ("9-8", "Wild Card Bubble", "🫧")

    assert project_season_record(110.0) == ("8-9", "Draft Lottery Bound", "🎟️")
    assert project_season_record(50.0) == ("2-15", "Draft Lottery Bound", "🎟️")
    assert project_season_record(10.0) == ("0-17", "Draft Lottery Bound", "🎟️")


def test_chemistry_same_team_season_and_legendary():
    p1 = RosterPlayer(
        player_id="00-0033873",
        name="Patrick Mahomes",
        position="QB",
        slot="QB",
        drafted_team="KC",
        drafted_season=2018,
        base_fppg=28.9,
        college="Texas Tech",
        draft_year=2017,
        career_teams={"KC"},
    )
    p2 = RosterPlayer(
        player_id="00-0030506",
        name="Travis Kelce",
        position="TE",
        slot="TE",
        drafted_team="KC",
        drafted_season=2018,
        base_fppg=18.5,
        college="Cincinnati",
        draft_year=2013,
        career_teams={"KC"},
    )

    special_connections = {
        ("00-0030506", "00-0033873"): ("LEGENDARY", "Mahomes to Kelce"),
    }

    roster = {"QB": p1, "TE": p2}
    breakdown = calculate_chemistry(roster, special_connections=special_connections)

    # Base FPPG = 28.9 + 18.5 = 47.4
    assert breakdown.base_fppg == 47.4
    # Chemistry: Same Team (Rolled Season) +4 (+2 each), Legendary Connection +4 (+2 each) = +8.0
    assert breakdown.chemistry_fppg == 8.0
    assert breakdown.total_score == 55.4
    assert len(breakdown.active_links) == 2


def test_chemistry_mutual_exclusivity():
    p1 = RosterPlayer(
        player_id="P1",
        name="Player 1",
        position="WR",
        slot="WR1",
        drafted_team="NE",
        drafted_season=2015,
        base_fppg=15.0,
        career_teams={"NE", "TB"},
    )
    p2 = RosterPlayer(
        player_id="P2",
        name="Player 2",
        position="TE",
        slot="TE",
        drafted_team="TB",
        drafted_season=2020,
        base_fppg=12.0,
        career_teams={"NE", "TB"},
    )

    roster = {"WR1": p1, "TE": p2}
    breakdown = calculate_chemistry(roster)

    # Different drafted season & team, but shared career team 'NE' and 'TB' -> Past Teammates +1 each (+2 team)
    assert breakdown.chemistry_fppg == 2.0
    assert breakdown.total_score == 29.0
    assert any(link.bonus_type == "PAST_TEAMMATES" for link in breakdown.active_links)


def test_chemistry_same_college_and_draft_year():
    p1 = RosterPlayer(
        player_id="C1",
        name="LSU WR 1",
        position="WR",
        slot="WR1",
        drafted_team="CIN",
        drafted_season=2021,
        base_fppg=18.0,
        college="LSU",
        draft_year=2020,
    )
    p2 = RosterPlayer(
        player_id="C2",
        name="LSU WR 2",
        position="WR",
        slot="WR2",
        drafted_team="MIN",
        drafted_season=2020,
        base_fppg=17.0,
        college="LSU",
        draft_year=2020,
    )

    roster = {"WR1": p1, "WR2": p2}
    breakdown = calculate_chemistry(roster)

    # Same Draft Year (+1 each = +2) + Same College (+2 each = +4) = +6 total
    assert breakdown.chemistry_fppg == 6.0
    assert breakdown.total_score == 41.0
    assert len(breakdown.active_links) == 2
