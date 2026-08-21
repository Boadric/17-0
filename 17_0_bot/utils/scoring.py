from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    from config import get_canonical_team
except (ImportError, ValueError):
    from ..config import get_canonical_team


@dataclass
class RosterPlayer:
    player_id: str
    name: str
    position: str  # 'QB', 'RB', 'WR', 'TE'
    slot: str      # 'QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLX'
    drafted_team: str
    drafted_season: int
    base_fppg: float
    college: Optional[str] = None
    draft_year: Optional[int] = None
    headshot_url: Optional[str] = None
    espn_id: Optional[str] = None
    career_teams: Set[str] = field(default_factory=set)  # Set of team codes player played for in career
    # Chemistry tags applied to this specific player (e.g., ["Same Team +2", "Legendary +2"])
    applied_bonuses: List[str] = field(default_factory=list)
    chemistry_fppg: float = 0.0

    @property
    def total_fppg(self) -> float:
        return round(self.base_fppg + self.chemistry_fppg, 2)


@dataclass
class ChemistryLink:
    player1_name: str
    player1_slot: str
    player2_name: str
    player2_slot: str
    bonus_type: str  # 'SAME_TEAM_SEASON', 'PAST_TEAMMATES', 'SAME_DRAFT_YEAR', 'SAME_COLLEGE', 'ELITE', 'LEGENDARY'
    description: str
    player_bonus: float  # Bonus added to EACH player
    team_bonus: float    # Total added to team (= player_bonus * 2)


@dataclass
class ScoringBreakdown:
    base_fppg: float
    chemistry_fppg: float
    total_score: float
    projected_record: str
    tier_name: str
    tier_badge: str
    active_links: List[ChemistryLink] = field(default_factory=list)


def calculate_chemistry(
    roster: Dict[str, RosterPlayer],
    special_connections: Optional[Dict[Tuple[str, str], Tuple[str, str]]] = None,
    career_teammates_map: Optional[Set[Tuple[str, str]]] = None,
) -> ScoringBreakdown:
    """
    Evaluates chemistry bonuses for all unique pairs in the roster.
    
    special_connections: dict mapping (id1, id2) -> (connection_type, label)
    career_teammates_map: set of (id1, id2) where id1 < id2 who were past teammates
    """
    if special_connections is None:
        special_connections = {}
    if career_teammates_map is None:
        career_teammates_map = set()

    # Reset player bonuses
    for player in roster.values():
        player.applied_bonuses.clear()
        player.chemistry_fppg = 0.0

    active_links: List[ChemistryLink] = []
    slots = list(roster.keys())
    n = len(slots)

    # Pairwise evaluation
    for i in range(n):
        slot1 = slots[i]
        p1 = roster[slot1]
        for j in range(i + 1, n):
            slot2 = slots[j]
            p2 = roster[slot2]

            # 1. Same Team (Rolled Season) vs Past Teammates (Mutually Exclusive)
            p1_canon_team = get_canonical_team(p1.drafted_team)
            p2_canon_team = get_canonical_team(p2.drafted_team)

            is_same_rolled_team_season = (
                p1_canon_team == p2_canon_team
                and p1.drafted_season == p2.drafted_season
            )

            if is_same_rolled_team_season:
                # Same Team (Rolled Season): +2 each (+4 team total)
                p1.chemistry_fppg += 2.0
                p2.chemistry_fppg += 2.0
                p1.applied_bonuses.append(f"Same Team ({p1_canon_team} '{str(p1.drafted_season)[2:]}) +2")
                p2.applied_bonuses.append(f"Same Team ({p2_canon_team} '{str(p2.drafted_season)[2:]}) +2")
                active_links.append(ChemistryLink(
                    player1_name=p1.name,
                    player1_slot=p1.slot,
                    player2_name=p2.name,
                    player2_slot=p2.slot,
                    bonus_type="SAME_TEAM_SEASON",
                    description=f"Same Team ({p1_canon_team} {p1.drafted_season})",
                    player_bonus=2.0,
                    team_bonus=4.0,
                ))
            else:
                # Check Past Teammates: +1 each (+2 team total)
                pair_key = tuple(sorted([p1.player_id, p2.player_id]))
                is_career_teammates = (
                    pair_key in career_teammates_map
                    or bool(p1.career_teams and p2.career_teams and (p1.career_teams & p2.career_teams))
                )
                if is_career_teammates:
                    p1.chemistry_fppg += 1.0
                    p2.chemistry_fppg += 1.0
                    p1.applied_bonuses.append("Past Teammates +1")
                    p2.applied_bonuses.append("Past Teammates +1")
                    active_links.append(ChemistryLink(
                        player1_name=p1.name,
                        player1_slot=p1.slot,
                        player2_name=p2.name,
                        player2_slot=p2.slot,
                        bonus_type="PAST_TEAMMATES",
                        description="Past Teammates",
                        player_bonus=1.0,
                        team_bonus=2.0,
                    ))

            # 2. Same Draft Year: +1 each (+2 team total)
            if p1.draft_year and p2.draft_year and p1.draft_year == p2.draft_year:
                p1.chemistry_fppg += 1.0
                p2.chemistry_fppg += 1.0
                p1.applied_bonuses.append(f"Draft Class ({p1.draft_year}) +1")
                p2.applied_bonuses.append(f"Draft Class ({p2.draft_year}) +1")
                active_links.append(ChemistryLink(
                    player1_name=p1.name,
                    player1_slot=p1.slot,
                    player2_name=p2.name,
                    player2_slot=p2.slot,
                    bonus_type="SAME_DRAFT_YEAR",
                    description=f"Same Draft Class ({p1.draft_year})",
                    player_bonus=1.0,
                    team_bonus=2.0,
                ))

            # 3. Same College: +2 each (+4 team total)
            if (
                p1.college
                and p2.college
                and p1.college.strip().lower() == p2.college.strip().lower()
                and p1.college.strip().lower() not in ("none", "n/a", "")
            ):
                p1.chemistry_fppg += 2.0
                p2.chemistry_fppg += 2.0
                p1.applied_bonuses.append(f"College ({p1.college}) +2")
                p2.applied_bonuses.append(f"College ({p2.college}) +2")
                active_links.append(ChemistryLink(
                    player1_name=p1.name,
                    player1_slot=p1.slot,
                    player2_name=p2.name,
                    player2_slot=p2.slot,
                    bonus_type="SAME_COLLEGE",
                    description=f"Alma Mater ({p1.college})",
                    player_bonus=2.0,
                    team_bonus=4.0,
                ))

            # 4. Special Connections (Elite / Legendary)
            pair_key = tuple(sorted([p1.player_id, p2.player_id]))
            conn = special_connections.get(pair_key)
            if not conn:
                conn = special_connections.get((p1.player_id, p2.player_id)) or special_connections.get((p2.player_id, p1.player_id))

            if conn:
                conn_type, label = conn
                conn_type = conn_type.upper()
                if conn_type == "LEGENDARY":
                    p1.chemistry_fppg += 2.0
                    p2.chemistry_fppg += 2.0
                    p1.applied_bonuses.append(f"Legendary Connection ({label}) +2")
                    p2.applied_bonuses.append(f"Legendary Connection ({label}) +2")
                    active_links.append(ChemistryLink(
                        player1_name=p1.name,
                        player1_slot=p1.slot,
                        player2_name=p2.name,
                        player2_slot=p2.slot,
                        bonus_type="LEGENDARY",
                        description=f"Legendary: {label}",
                        player_bonus=2.0,
                        team_bonus=4.0,
                    ))
                elif conn_type == "ELITE":
                    p1.chemistry_fppg += 1.0
                    p2.chemistry_fppg += 1.0
                    p1.applied_bonuses.append(f"Elite Connection ({label}) +1")
                    p2.applied_bonuses.append(f"Elite Connection ({label}) +1")
                    active_links.append(ChemistryLink(
                        player1_name=p1.name,
                        player1_slot=p1.slot,
                        player2_name=p2.name,
                        player2_slot=p2.slot,
                        bonus_type="ELITE",
                        description=f"Elite: {label}",
                        player_bonus=1.0,
                        team_bonus=2.0,
                    ))

    base_fppg = round(sum(p.base_fppg for p in roster.values()), 2)
    chemistry_fppg = round(sum(link.team_bonus for link in active_links), 2)
    total_score = round(base_fppg + chemistry_fppg, 2)

    projected_record, tier_name, tier_badge = project_season_record(total_score)

    return ScoringBreakdown(
        base_fppg=base_fppg,
        chemistry_fppg=chemistry_fppg,
        total_score=total_score,
        projected_record=projected_record,
        tier_name=tier_name,
        tier_badge=tier_badge,
        active_links=active_links,
    )


def project_season_record(score: float) -> Tuple[str, str, str]:
    """
    Returns (projected_record, tier_name, tier_badge) based on total FPPG score.
    """
    if score >= 160.0:
        return "17-0", "Undefeated Champion", "🏆"
    elif score >= 145.0:
        if score >= 152.5:
            record = "16-1"
        else:
            record = "15-2"
        return record, "Super Bowl Contender", "💍"
    elif score >= 130.0:
        if score >= 140.0:
            record = "14-3"
        elif score >= 135.0:
            record = "13-4"
        else:
            record = "12-5"
        return record, "Playoff Lock", "🔒"
    elif score >= 115.0:
        if score >= 125.0:
            record = "11-6"
        elif score >= 120.0:
            record = "10-7"
        else:
            record = "9-8"
        return record, "Wild Card Bubble", "🫧"
    else:
        if score >= 105.0:
            record = "8-9"
        elif score >= 95.0:
            record = "7-10"
        elif score >= 85.0:
            record = "6-11"
        elif score >= 75.0:
            record = "5-12"
        elif score >= 65.0:
            record = "4-13"
        elif score >= 55.0:
            record = "3-14"
        elif score >= 45.0:
            record = "2-15"
        elif score >= 35.0:
            record = "1-16"
        else:
            record = "0-17"
        return record, "Draft Lottery Bound", "🎟️"
