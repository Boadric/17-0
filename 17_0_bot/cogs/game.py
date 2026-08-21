import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
import discord
from discord import app_commands
from discord.ext import commands

try:
    from config import (
        APPLICATION_ID,
        DB_PATH,
        NFL_TEAMS,
        POSITION_TO_SLOTS,
        ROSTER_SLOTS,
        SLOT_ELIGIBILITY,
        TOTAL_ROUNDS,
        get_canonical_team,
        get_team_display_name,
    )
    from database import (
        get_career_teammates_map,
        get_leaderboard,
        get_player_by_id_and_team,
        get_player_by_name_and_team,
        get_player_career_teams,
        get_random_season_for_team,
        get_random_team_for_season,
        get_random_team_season,
        get_special_connections_for_players,
        save_to_leaderboard,
        search_players_on_team,
    )
    from utils.scoring import RosterPlayer, ScoringBreakdown, calculate_chemistry
except (ImportError, ValueError):
    from ..config import (
        APPLICATION_ID,
        DB_PATH,
        NFL_TEAMS,
        POSITION_TO_SLOTS,
        ROSTER_SLOTS,
        SLOT_ELIGIBILITY,
        TOTAL_ROUNDS,
        get_canonical_team,
        get_team_display_name,
    )
    from ..database import (
        get_career_teammates_map,
        get_leaderboard,
        get_player_by_id_and_team,
        get_player_by_name_and_team,
        get_player_career_teams,
        get_random_season_for_team,
        get_random_team_for_season,
        get_random_team_season,
        get_special_connections_for_players,
        save_to_leaderboard,
        search_players_on_team,
    )
    from ..utils.scoring import RosterPlayer, ScoringBreakdown, calculate_chemistry

logger = logging.getLogger(__name__)


class GameSession:
    """State machine representing an active 17-0 game session."""

    def __init__(self, user_id: int, username: str, channel_id: int, db_path: str = DB_PATH):
        self.user_id = user_id
        self.username = username
        self.channel_id = channel_id
        self.db_path = db_path
        self.round_num = 1
        self.roster: Dict[str, RosterPlayer] = {}
        self.team_rerolls_left = 1
        self.year_rerolls_left = 1
        self.current_team = "DEN"
        self.current_season = 2011
        self.position_filter: Optional[str] = None  # None means 'All'
        self.available_players: List[Dict[str, Any]] = []
        self.is_over = False
        self.saved_to_leaderboard = False
        self.breakdown: Optional[ScoringBreakdown] = None

    async def initialize(self):
        """Rolls the initial team and season and loads available players."""
        self.current_team, self.current_season = await get_random_team_season(db_path=self.db_path)
        await self.refresh_available_players()
        await self.recalculate_score()

    def get_open_slots_for_position(self, position: str) -> List[str]:
        """Returns list of open slots eligible for a given position."""
        eligible_slots = POSITION_TO_SLOTS.get(position.upper(), [])
        return [slot for slot in eligible_slots if slot not in self.roster]

    def auto_assign_slot(self, position: str) -> Optional[str]:
        """Automatically assigns a player to the next appropriate open slot."""
        pos = position.upper()
        if pos == "QB":
            return "QB" if "QB" not in self.roster else None
        elif pos == "RB":
            if "RB1" not in self.roster:
                return "RB1"
            elif "RB2" not in self.roster:
                return "RB2"
            elif "FLX" not in self.roster:
                return "FLX"
            return None
        elif pos == "WR":
            if "WR1" not in self.roster:
                return "WR1"
            elif "WR2" not in self.roster:
                return "WR2"
            elif "FLX" not in self.roster:
                return "FLX"
            return None
        elif pos == "TE":
            if "TE" not in self.roster:
                return "TE"
            elif "FLX" not in self.roster:
                return "FLX"
            return None
        return None

    def get_eligible_positions(self) -> List[str]:
        """Returns list of positions ('QB', 'RB', 'WR', 'TE') that still have at least 1 open slot."""
        return [pos for pos in ["QB", "RB", "WR", "TE"] if self.auto_assign_slot(pos) is not None]

    async def refresh_available_players(self):
        """Fetches available players for current franchise/season, strictly restricted to open positions."""
        eligible = self.get_eligible_positions()

        if self.position_filter:
            positions = [self.position_filter] if self.position_filter in eligible else []
        else:
            positions = eligible

        self.available_players = await search_players_on_team(
            team=self.current_team,
            season=self.current_season,
            positions=positions,
            limit=25,
            db_path=self.db_path,
        )

    async def recalculate_score(self) -> ScoringBreakdown:
        """Queries connections and recalculates the team's chemistry and score."""
        player_ids = [p.player_id for p in self.roster.values()]
        if len(player_ids) >= 2:
            try:
                teammates_map = await get_career_teammates_map(player_ids, db_path=self.db_path)
                special_conn = await get_special_connections_for_players(player_ids, db_path=self.db_path)
            except Exception as e:
                logger.warning("Error querying chemistry relations: %s", e)
                teammates_map = set()
                special_conn = {}
        else:
            teammates_map = set()
            special_conn = {}

        self.breakdown = calculate_chemistry(
            self.roster,
            special_connections=special_conn,
            career_teammates_map=teammates_map,
        )
        return self.breakdown

    def build_active_embed(self) -> discord.Embed:
        """Constructs the rich Discord Embed for the active game state."""
        canon = get_canonical_team(self.current_team)
        team_info = NFL_TEAMS.get(canon, {})
        team_name = get_team_display_name(canon, self.current_season)
        color = team_info.get("color", 0x0080C6)
        emoji = team_info.get("emoji", "🏈")

        eligible_positions = self.get_eligible_positions()
        if self.position_filter:
            filter_label = self.position_filter
        elif len(eligible_positions) == 4:
            filter_label = "All Positions"
        else:
            filter_label = f"Eligible: {', '.join(eligible_positions)}" if eligible_positions else "Roster Full"

        embed = discord.Embed(
            title=f"🏈 17-0 Game — Round {self.round_num}/{TOTAL_ROUNDS}",
            description=(
                f"## {emoji} **{self.current_season} {team_name}** (`{canon}`)\n"
                f"Select a player from the dropdown below or click **Search Name** to draft!"
            ),
            color=color,
        )

        # 1. Available Players List Field (Mobile App Style)
        if self.available_players:
            player_lines = []
            for p in self.available_players[:10]:
                pos = p["position"]
                fppg = float(p.get("ppr_fppg") or 0.0)
                name = p["name"]
                college = p.get("college") or "N/A"
                draft_yr = p.get("draft_year")
                draft_str = f"Draft '{str(draft_yr)[2:]}" if draft_yr else "UDFA"

                already_drafted = any(dp.player_id == p["player_id"] for dp in self.roster.values())
                if already_drafted:
                    player_lines.append(f"~~`{pos:<2}` **{name}** — `{fppg:.1f}` FPPG *(Drafted)*~~")
                else:
                    player_lines.append(f"`{pos:<2}` **{name}** — **`{fppg:.1f}`** FPPG *({college} · {draft_str})*")

            if len(self.available_players) > 10:
                player_lines.append(f"*+ {len(self.available_players) - 10} more in the dropdown below...*")

            embed.add_field(
                name=f"📋 Available Weapons ({filter_label})",
                value="\n".join(player_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"📋 Available Weapons ({filter_label})",
                value="*No available players found for your open roster slots on this team.*",
                inline=False,
            )

        # 2. Active Fantasy Roster Grid Field
        roster_lines = []
        for slot in ROSTER_SLOTS:
            if slot in self.roster:
                p = self.roster[slot]
                canon_pteam = get_canonical_team(p.drafted_team)
                bonuses_str = ""
                if p.applied_bonuses:
                    bonuses_str = f" ⚡ *({', '.join(p.applied_bonuses)})*"
                roster_lines.append(
                    f"**{slot:<4}**: **{p.name}** ({p.drafted_season} {canon_pteam}) — `{p.base_fppg:.1f}` FPPG{bonuses_str}"
                )
            else:
                eligible = ", ".join(SLOT_ELIGIBILITY[slot])
                roster_lines.append(f"**{slot:<4}**: `[Empty - {eligible}]`")

        embed.add_field(name=f"👥 Active Fantasy Roster ({len(self.roster)}/{TOTAL_ROUNDS})", value="\n".join(roster_lines), inline=False)

        # 3. Score Summary Field
        if self.breakdown:
            b_fppg = self.breakdown.base_fppg
            c_fppg = self.breakdown.chemistry_fppg
            t_score = self.breakdown.total_score
            rec = self.breakdown.projected_record
            badge = self.breakdown.tier_badge
            tier = self.breakdown.tier_name

            score_text = (
                f"**Base FPPG:** `{b_fppg:.1f}` | **Chemistry:** `+{c_fppg:.1f}` | **Total:** `{t_score:.1f}`\n"
                f"**Projected Record:** {badge} **{rec}** ({tier})"
            )
        else:
            score_text = "**Base FPPG:** `0.0` | **Chemistry:** `+0.0` | **Total:** `0.0`"

        embed.add_field(name="📊 Team Projection", value=score_text, inline=False)
        embed.set_footer(text=f"Drafting: {self.username} • 17-0 NFL Strategy Bot")
        return embed

    def build_game_over_embed(self) -> discord.Embed:
        """Constructs the rich Discord Embed for the final completed roster."""
        badge = self.breakdown.tier_badge if self.breakdown else "🏈"
        rec = self.breakdown.projected_record if self.breakdown else "17-0"
        tier = self.breakdown.tier_name if self.breakdown else "Champion"

        embed = discord.Embed(
            title=f"{badge} Game Complete — Final Record: {rec}",
            description=f"Congratulations **{self.username}**! You assembled a **{tier}** roster!",
            color=0xFFD700 if rec == "17-0" else 0x00FF88,
        )

        roster_lines = []
        for slot in ROSTER_SLOTS:
            p = self.roster[slot]
            canon_pteam = get_canonical_team(p.drafted_team)
            bonuses = f" ⚡ *({', '.join(p.applied_bonuses)})*" if p.applied_bonuses else ""
            roster_lines.append(
                f"**{slot}**: **{p.name}** ({p.drafted_season} {canon_pteam}) — `{p.base_fppg:.1f}` FPPG{bonuses}"
            )
        embed.add_field(name="🏆 Final 7-Man Fantasy Roster", value="\n".join(roster_lines), inline=False)

        # Chemistry Links Summary
        if self.breakdown and self.breakdown.active_links:
            links_lines = [
                f"• **{l.player1_name}** ({l.player1_slot}) & **{l.player2_name}** ({l.player2_slot}): {l.description} (`+{l.team_bonus:.0f}` Team)"
                for l in self.breakdown.active_links
            ]
            embed.add_field(name="⚡ Active Chemistry Links", value="\n".join(links_lines), inline=False)

        # Final Totals
        if self.breakdown:
            summary = (
                f"**Base FPPG:** `{self.breakdown.base_fppg:.1f}`\n"
                f"**Chemistry Link Bonus:** `+{self.breakdown.chemistry_fppg:.1f}`\n"
                f"**Final Total Score:** **`{self.breakdown.total_score:.1f}` FPPG**\n"
                f"**Projected Regular Season:** {badge} **`{rec}` ({tier})**"
            )
            embed.add_field(name="📈 Final Score Breakdown", value=summary, inline=False)

        embed.set_footer(text=f"Draft completed by {self.username}")
        return embed


class PlayerSelectDropdown(discord.ui.Select):
    """Dropdown component populated with available players for direct 1-click drafting."""

    def __init__(self, session: GameSession, parent_view: "ActiveGameView"):
        self.session = session
        self.parent_view = parent_view

        options = []
        for p in session.available_players[:25]:
            pid = p["player_id"]
            name = p["name"]
            pos = p["position"]
            fppg = float(p.get("ppr_fppg") or 0.0)
            college = p.get("college") or "N/A"
            draft_yr = p.get("draft_year")
            draft_str = f"Draft '{str(draft_yr)[2:]}" if draft_yr else "UDFA"

            already_drafted = any(dp.player_id == pid for dp in session.roster.values())
            desc = f"{fppg:.1f} FPPG • {college} ({draft_str})"
            if already_drafted:
                desc = f"[Drafted] {desc}"

            options.append(
                discord.SelectOption(
                    label=f"{name} ({pos})",
                    value=pid,
                    description=desc[:100],
                    emoji="🏈" if pos == "QB" else ("🏃" if pos == "RB" else ("⚡" if pos == "WR" else "🎯")),
                )
            )

        if not options:
            options = [
                discord.SelectOption(
                    label="No available players for open slots",
                    value="none",
                    description="Try rerolling the team/year or custom search",
                )
            ]

        super().__init__(
            placeholder="⚡ Select a player to draft...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This is not your game session!", ephemeral=True)
            return

        selected_pid = self.values[0]
        if selected_pid == "none":
            await interaction.response.send_message("Please select a valid player.", ephemeral=True)
            return

        player_data = await get_player_by_id_and_team(
            player_id=selected_pid,
            team=self.session.current_team,
            season=self.session.current_season,
            db_path=self.session.db_path,
        )

        if not player_data:
            await interaction.response.send_message("❌ Player data not found!", ephemeral=True)
            return

        for slot, drafted in self.session.roster.items():
            if drafted.player_id == player_data["player_id"]:
                await interaction.response.send_message(
                    f"❌ **{player_data['name']}** is already on your roster in slot **{slot}**!",
                    ephemeral=True,
                )
                return

        pos = player_data["position"].upper()
        slot = self.session.auto_assign_slot(pos)

        if not slot:
            eligible_for_pos = ", ".join(POSITION_TO_SLOTS.get(pos, []))
            await interaction.response.send_message(
                f"❌ All eligible roster slots for position **{pos}** ({eligible_for_pos}) are full!\n"
                f"Please draft a player for an unfilled position.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        career_teams = await get_player_career_teams(player_data["player_id"], db_path=self.session.db_path)

        drafted_obj = RosterPlayer(
            player_id=player_data["player_id"],
            name=player_data["name"],
            position=pos,
            slot=slot,
            drafted_team=self.session.current_team,
            drafted_season=self.session.current_season,
            base_fppg=float(player_data["ppr_fppg"] or 0.0),
            college=player_data.get("college"),
            draft_year=player_data.get("draft_year"),
            career_teams=career_teams,
        )

        self.session.roster[slot] = drafted_obj
        await self.parent_view.advance_after_draft()


class SearchPlayerModal(discord.ui.Modal, title="Search & Draft Player"):
    """Modal for custom name search if a player is not in top dropdown."""

    player_name = discord.ui.TextInput(
        label="Player Name",
        placeholder="e.g. Tim Tebow, Willis McGahee, Eric Decker",
        min_length=2,
        max_length=60,
        required=True,
    )

    def __init__(self, session: GameSession, parent_view: "ActiveGameView"):
        super().__init__()
        self.session = session
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        query = self.player_name.value.strip()

        player_data = await get_player_by_name_and_team(
            name_query=query,
            team=self.session.current_team,
            season=self.session.current_season,
            db_path=self.session.db_path,
        )

        if not player_data:
            top_players = await search_players_on_team(
                team=self.session.current_team,
                season=self.session.current_season,
                positions=self.session.get_eligible_positions(),
                limit=6,
                db_path=self.session.db_path,
            )
            suggestions = ", ".join([f"{p['name']} ({p['position']})" for p in top_players]) if top_players else "None"
            await interaction.response.send_message(
                f"❌ **{query}** was not found on the **{self.session.current_season} {get_canonical_team(self.session.current_team)}** roster!\n"
                f"💡 *Available players for open slots:* {suggestions}",
                ephemeral=True,
            )
            return

        for slot, drafted in self.session.roster.items():
            if drafted.player_id == player_data["player_id"]:
                await interaction.response.send_message(
                    f"❌ **{player_data['name']}** is already on your roster in slot **{slot}**!",
                    ephemeral=True,
                )
                return

        pos = player_data["position"].upper()
        slot = self.session.auto_assign_slot(pos)

        if not slot:
            eligible_for_pos = ", ".join(POSITION_TO_SLOTS.get(pos, []))
            await interaction.response.send_message(
                f"❌ All eligible roster slots for position **{pos}** ({eligible_for_pos}) are full!",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        career_teams = await get_player_career_teams(player_data["player_id"], db_path=self.session.db_path)

        drafted_obj = RosterPlayer(
            player_id=player_data["player_id"],
            name=player_data["name"],
            position=pos,
            slot=slot,
            drafted_team=self.session.current_team,
            drafted_season=self.session.current_season,
            base_fppg=float(player_data["ppr_fppg"] or 0.0),
            college=player_data.get("college"),
            draft_year=player_data.get("draft_year"),
            career_teams=career_teams,
        )

        self.session.roster[slot] = drafted_obj
        await self.parent_view.advance_after_draft()


class ActiveGameView(discord.ui.View):
    """Main interactive Discord View for an active 17-0 game with filters, dropdowns and rerolls."""

    def __init__(self, session: GameSession):
        super().__init__(timeout=300)
        self.session = session
        self.message: Optional[discord.Message] = None
        self.rebuild_view()

    def rebuild_view(self):
        """Rebuilds the interactive components (dropdown, position filter buttons, reroll buttons)."""
        self.clear_items()

        # Row 0: Player Select Dropdown
        self.add_item(PlayerSelectDropdown(session=self.session, parent_view=self))

        # Row 1: Position Filter Buttons
        eligible_positions = self.session.get_eligible_positions()

        # "All" Button
        is_all_active = self.session.position_filter is None
        all_btn = discord.ui.Button(
            label="All",
            style=discord.ButtonStyle.success if is_all_active else discord.ButtonStyle.secondary,
            custom_id="filter_all",
            row=1,
        )
        all_btn.callback = self.make_filter_callback(None)
        self.add_item(all_btn)

        # Position specific buttons (disabled if position has 0 open slots)
        for pos in ["QB", "RB", "WR", "TE"]:
            is_eligible = pos in eligible_positions
            is_active = self.session.position_filter == pos
            style = discord.ButtonStyle.success if is_active else discord.ButtonStyle.secondary

            btn = discord.ui.Button(
                label=pos if is_eligible else f"{pos} (Full)",
                style=style,
                disabled=not is_eligible,
                custom_id=f"filter_{pos.lower()}",
                row=1,
            )
            btn.callback = self.make_filter_callback(pos)
            self.add_item(btn)

        # Row 2: Action Buttons (Team Reroll, Year Reroll, Manual Search)
        team_reroll_btn = discord.ui.Button(
            label=f"🎲 Reroll Team ({self.session.team_rerolls_left})",
            style=discord.ButtonStyle.primary,
            disabled=self.session.team_rerolls_left <= 0,
            row=2,
        )
        team_reroll_btn.callback = self.on_reroll_team
        self.add_item(team_reroll_btn)

        year_reroll_btn = discord.ui.Button(
            label=f"📅 Reroll Year ({self.session.year_rerolls_left})",
            style=discord.ButtonStyle.primary,
            disabled=self.session.year_rerolls_left <= 0,
            row=2,
        )
        year_reroll_btn.callback = self.on_reroll_year
        self.add_item(year_reroll_btn)

        search_btn = discord.ui.Button(
            label="🔍 Search Name",
            style=discord.ButtonStyle.secondary,
            row=2,
        )
        search_btn.callback = self.on_search_modal
        self.add_item(search_btn)

    def make_filter_callback(self, position: Optional[str]):
        async def filter_callback(interaction: discord.Interaction):
            if interaction.user.id != self.session.user_id:
                await interaction.response.send_message("❌ This is not your game session!", ephemeral=True)
                return
            await interaction.response.defer()
            self.session.position_filter = position
            await self.session.refresh_available_players()
            self.rebuild_view()
            embed = self.session.build_active_embed()
            if self.message:
                await self.message.edit(embed=embed, view=self)

        return filter_callback

    async def on_reroll_team(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This is not your game session!", ephemeral=True)
            return

        if self.session.team_rerolls_left <= 0:
            await interaction.response.send_message("❌ You have no team rerolls remaining!", ephemeral=True)
            return

        await interaction.response.defer()
        self.session.team_rerolls_left -= 1
        new_team = await get_random_team_for_season(
            self.session.current_season, self.session.current_team, db_path=self.session.db_path
        )
        self.session.current_team = new_team
        await self.session.refresh_available_players()
        self.rebuild_view()

        embed = self.session.build_active_embed()
        if self.message:
            await self.message.edit(embed=embed, view=self)

    async def on_reroll_year(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This is not your game session!", ephemeral=True)
            return

        if self.session.year_rerolls_left <= 0:
            await interaction.response.send_message("❌ You have no year rerolls remaining!", ephemeral=True)
            return

        await interaction.response.defer()
        self.session.year_rerolls_left -= 1
        new_year = await get_random_season_for_team(
            self.session.current_team, self.session.current_season, db_path=self.session.db_path
        )
        self.session.current_season = new_year
        await self.session.refresh_available_players()
        self.rebuild_view()

        embed = self.session.build_active_embed()
        if self.message:
            await self.message.edit(embed=embed, view=self)

    async def on_search_modal(self, interaction: discord.Interaction):
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message("❌ This is not your game session!", ephemeral=True)
            return
        modal = SearchPlayerModal(session=self.session, parent_view=self)
        await interaction.response.send_modal(modal)

    async def advance_after_draft(self):
        """Advances round or transitions to Game Over once 7 slots are filled."""
        await self.session.recalculate_score()

        if len(self.session.roster) >= TOTAL_ROUNDS:
            self.session.is_over = True
            game_over_view = GameOverView(self.session)
            embed = self.session.build_game_over_embed()

            if self.message:
                await self.message.edit(embed=embed, view=game_over_view)
            return

        # Advance to next round
        self.session.round_num += 1
        self.session.position_filter = None
        self.session.current_team, self.session.current_season = await get_random_team_season(db_path=self.session.db_path)
        await self.session.refresh_available_players()
        self.rebuild_view()

        embed = self.session.build_active_embed()
        if self.message:
            await self.message.edit(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class GameOverView(discord.ui.View):
    """View displayed when the game finishes."""

    def __init__(self, session: GameSession):
        super().__init__(timeout=300)
        self.session = session

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message(
                "❌ This is not your game session! Start your own with `/17-0 play`.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Save to Leaderboard", style=discord.ButtonStyle.success, emoji="💾", row=0)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.session.saved_to_leaderboard:
            await interaction.response.send_message("ℹ️ This game has already been saved to the leaderboard!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if not self.session.breakdown:
            await self.session.recalculate_score()

        row_id = await save_to_leaderboard(
            user_id=str(self.session.user_id),
            username=self.session.username,
            total_score=self.session.breakdown.total_score,
            projected_record=self.session.breakdown.projected_record,
            roster=self.session.roster,
            db_path=self.session.db_path,
        )
        self.session.saved_to_leaderboard = True
        button.disabled = True
        button.label = "Saved to Leaderboard ✅"
        await interaction.message.edit(view=self)
        await interaction.followup.send(
            f"🎉 Roster saved to leaderboard with score **{self.session.breakdown.total_score:.1f} FPPG** ({self.session.breakdown.projected_record})!",
            ephemeral=True,
        )

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def play_again_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        new_session = GameSession(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            channel_id=interaction.channel_id,
            db_path=self.session.db_path,
        )
        await new_session.initialize()
        view = ActiveGameView(new_session)
        embed = new_session.build_active_embed()
        msg = await interaction.followup.send(embed=embed, view=view)
        view.message = msg


class SeventeenZeroCog(commands.GroupCog, name="17-0", description="17-0 NFL Draft & Chemistry Strategy Game"):
    """GroupCog for the 17-0 NFL Draft & Chemistry Strategy Game."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="play", description="Start a new 17-0 NFL draft game session!")
    async def play(self, interaction: discord.Interaction):
        await interaction.response.defer()

        session = GameSession(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            channel_id=interaction.channel_id,
        )
        await session.initialize()
        view = ActiveGameView(session)
        embed = session.build_active_embed()

        msg = await interaction.followup.send(embed=embed, view=view)
        view.message = msg

    @app_commands.command(name="activity", description="Launch the interactive Discord Activity web game!")
    async def activity(self, interaction: discord.Interaction):
        app_id = APPLICATION_ID or "1540222119697322004"
        embed = discord.Embed(
            title="🎮 17-0 Discord Activity (Interactive Web Game)",
            description=(
                "Experience **17-0** with full visual cards, animations, sounds, and live chemistry link effects right inside Discord!\n\n"
                "### 🚀 How to Launch in Discord:\n"
                "1. Join any **Voice Channel** in this server.\n"
                "2. Click the **Rocket Icon (🚀 Activities)** at the bottom left.\n"
                "3. Select **17-0** to start playing together!\n\n"
                "*You can also play the web version directly in your browser:* [Open 17-0 Web App](https://17-0-production.up.railway.app/)"
            ),
            color=0x0080C6,
        )
        embed.set_footer(text="17-0 NFL Strategy Activity • Powered by Discord Embedded App SDK")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the top 10 highest-scoring 17-0 rosters!")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        entries = await get_leaderboard(limit=10)

        if not entries:
            embed = discord.Embed(
                title="🏆 17-0 Hall of Fame — Leaderboard",
                description="No games have been recorded on the leaderboard yet! Be the first by playing `/17-0 play`.",
                color=0xFFD700,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="🏆 17-0 Hall of Fame — Leaderboard",
            description="Top 10 highest-scoring NFL dream teams in 17-0 history:",
            color=0xFFD700,
        )

        for rank, entry in enumerate(entries, start=1):
            user = entry["username"]
            score = entry["total_score"]
            record = entry["projected_record"]
            roster = entry.get("roster", {})

            key_players = []
            for slot in ["QB", "WR1", "RB1", "TE"]:
                if slot in roster:
                    p = roster[slot]
                    key_players.append(f"{p.get('name', '')} ({p.get('drafted_season', '')})")

            stars_text = f"⭐ *Core:* {', '.join(key_players)}" if key_players else ""
            medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"#{rank}"))

            embed.add_field(
                name=f"{medal} {user} — {score:.1f} FPPG ({record})",
                value=f"{stars_text}\n*Recorded: {str(entry['created_at'])[:10]}*",
                inline=False,
            )

        embed.set_footer(text="Play and save your score with /17-0 play!")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rules", description="Learn how to play 17-0, roster slots, and chemistry rules.")
    async def rules(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 17-0 Game — Rules & Strategy Guide",
            description=(
                "**Goal:** Build a 7-man fantasy roster by rolling random historical NFL franchises and seasons (1999–2024). "
                "Stack Chemistry Links to maximize your Total FPPG and achieve the legendary **17-0** record!"
            ),
            color=0x00A86B,
        )

        embed.add_field(
            name="📋 Roster Positions (7 Total)",
            value=(
                "• **QB**: Quarterback\n"
                "• **RB1, RB2**: Running Backs\n"
                "• **WR1, WR2**: Wide Receivers\n"
                "• **TE**: Tight End\n"
                "• **FLX**: Flex spot (any RB, WR, or TE)"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚡ Chemistry Link Matrix (Stackable)",
            value=(
                "• **Same Draft Class**: `+1.0` each (`+2.0` Team) if drafted in the same NFL Draft year.\n"
                "• **Past Teammates**: `+1.0` each (`+2.0` Team) if ever on the same NFL roster in any year.\n"
                "• **Same Team & Season**: `+2.0` each (`+4.0` Team) if drafted from the exact same team & year *(mutually exclusive with Past Teammates)*.\n"
                "• **Same College**: `+2.0` each (`+4.0` Team) if attended the same university.\n"
                "• **Elite Connection**: `+1.0` each (`+2.0` Team) for iconic historical duos.\n"
                "• **Legendary Connection**: `+2.0` each (`+4.0` Team) for all-time great connections (e.g., Brady & Gronk, Mahomes & Kelce, Manning & Harrison)."
            ),
            inline=False,
        )

        embed.add_field(
            name="🎲 Rerolls & Turn Rules",
            value=(
                "• You get **1 Team Reroll** and **1 Year Reroll** per full game session.\n"
                "• When rolling a team and year, select a player from the dropdown or search by name. The bot automatically places them into your open slots!"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏆 Projected Regular Season Record Tiers",
            value=(
                "• **>= 160.0 FPPG**: 🏆 **17-0** (*Undefeated Champion*)\n"
                "• **145.0 – 159.9 FPPG**: 💍 **15-2 to 16-1** (*Super Bowl Contender*)\n"
                "• **130.0 – 144.9 FPPG**: 🔒 **12-5 to 14-3** (*Playoff Lock*)\n"
                "• **115.0 – 129.9 FPPG**: 🫧 **9-8 to 11-6** (*Wild Card Bubble*)\n"
                "• **< 115.0 FPPG**: 🎟️ **<= 8-9** (*Draft Lottery Bound*)"
            ),
            inline=False,
        )

        embed.set_footer(text="Ready to draft? Type /17-0 play or /17-0 activity!")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(SeventeenZeroCog(bot))
