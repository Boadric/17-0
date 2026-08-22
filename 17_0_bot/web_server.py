import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiohttp
from aiohttp import web

# Add package base directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from config import (
        APPLICATION_ID,
        DB_PATH,
        NFL_TEAMS,
        get_canonical_team,
        get_team_display_name,
    )
    from database import (
        get_career_teammates_map,
        get_leaderboard,
        get_player_career_teams,
        get_random_season_for_team,
        get_random_team_for_season,
        get_random_team_season,
        get_special_connections_for_players,
        save_to_leaderboard,
        search_players_on_team,
    )
    from utils.scoring import RosterPlayer, calculate_chemistry
except (ImportError, ValueError):
    from .config import (
        APPLICATION_ID,
        DB_PATH,
        NFL_TEAMS,
        get_canonical_team,
        get_team_display_name,
    )
    from .database import (
        get_career_teammates_map,
        get_leaderboard,
        get_player_career_teams,
        get_random_season_for_team,
        get_random_team_for_season,
        get_random_team_season,
        get_special_connections_for_players,
        save_to_leaderboard,
        search_players_on_team,
    )
    from .utils.scoring import RosterPlayer, calculate_chemistry

logger = logging.getLogger("17_0_web")
ACTIVITY_DIR = BASE_DIR / "activity"
if not ACTIVITY_DIR.exists():
    ACTIVITY_DIR = Path.cwd() / "activity"


def get_team_metadata(team: str, season: int) -> Dict[str, Any]:
    canon = get_canonical_team(team)
    team_info = NFL_TEAMS.get(canon, {})
    return {
        "team_code": canon,
        "team_name": get_team_display_name(canon, season),
        "color": f"#{team_info.get('color', 0x0080C6):06X}",
        "emoji": team_info.get("emoji", "🏈"),
    }


# --- REST API Endpoints ---

async def api_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "ok", "app": "17-0 Discord Activity"})


async def api_image_proxy(request: web.Request) -> web.Response:
    """Proxies external player headshots to bypass Discord iframe Content Security Policy."""
    url = request.query.get("url")
    if not url or not url.startswith("http"):
        return web.Response(status=400)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                if resp.status == 200:
                    body = await resp.read()
                    content_type = resp.headers.get("Content-Type", "image/png")
                    return web.Response(
                        body=body,
                        content_type=content_type,
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Cache-Control": "public, max-age=86400",
                        },
                    )
    except Exception as e:
        logger.debug("Image proxy fetch error for %s: %s", url, e)

    return web.Response(status=404)


async def api_roll(request: web.Request) -> web.Response:
    """Rolls a random team and season, returning available skill weapons with headshots."""
    team, season = await get_random_team_season()
    meta = get_team_metadata(team, season)
    players = await search_players_on_team(team=team, season=season, limit=25)

    return web.json_response({
        "team": meta["team_code"],
        "season": season,
        "team_name": meta["team_name"],
        "color": meta["color"],
        "emoji": meta["emoji"],
        "players": players,
    })


async def api_reroll_team(request: web.Request) -> web.Response:
    """Rerolls the team for a given season."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    season = int(data.get("season", 2020))
    current_team = data.get("current_team")
    new_team = await get_random_team_for_season(season, current_team)
    meta = get_team_metadata(new_team, season)

    positions = data.get("positions")
    players = await search_players_on_team(team=new_team, season=season, positions=positions, limit=25)

    return web.json_response({
        "team": meta["team_code"],
        "season": season,
        "team_name": meta["team_name"],
        "color": meta["color"],
        "emoji": meta["emoji"],
        "players": players,
    })


async def api_reroll_season(request: web.Request) -> web.Response:
    """Rerolls the season for a given franchise."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    team = data.get("team", "KC")
    current_season = int(data.get("current_season", 2020))
    new_season = await get_random_season_for_team(team, current_season)
    meta = get_team_metadata(team, new_season)

    positions = data.get("positions")
    players = await search_players_on_team(team=team, season=new_season, positions=positions, limit=25)

    return web.json_response({
        "team": meta["team_code"],
        "season": new_season,
        "team_name": meta["team_name"],
        "color": meta["color"],
        "emoji": meta["emoji"],
        "players": players,
    })


async def api_search_players(request: web.Request) -> web.Response:
    """Searches players on a specific team/season by name or eligible positions."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    team = data.get("team", "KC")
    season = int(data.get("season", 2020))
    query = data.get("query")
    positions = data.get("positions")

    players = await search_players_on_team(team=team, season=season, query=query, positions=positions, limit=25)
    return web.json_response({"players": players})


async def api_calculate(request: web.Request) -> web.Response:
    """Calculates chemistry bonuses and projected regular season record for a roster."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    roster_raw = data.get("roster", {})
    roster: Dict[str, RosterPlayer] = {}

    for slot, p_data in roster_raw.items():
        if not p_data or not p_data.get("player_id"):
            continue
        pid = p_data["player_id"]
        career_teams = await get_player_career_teams(pid)
        roster[slot] = RosterPlayer(
            player_id=pid,
            name=p_data.get("name", "Unknown"),
            position=p_data.get("position", "FLX"),
            slot=slot,
            drafted_team=p_data.get("drafted_team", "KC"),
            drafted_season=int(p_data.get("drafted_season", 2020)),
            base_fppg=float(p_data.get("base_fppg", 0.0)),
            college=p_data.get("college"),
            draft_year=p_data.get("draft_year"),
            headshot_url=p_data.get("headshot_url"),
            espn_id=p_data.get("espn_id"),
            career_teams=career_teams,
        )

    player_ids = [p.player_id for p in roster.values()]
    if len(player_ids) >= 2:
        teammates_map = await get_career_teammates_map(player_ids)
        special_conn = await get_special_connections_for_players(player_ids)
    else:
        teammates_map = set()
        special_conn = {}

    breakdown = calculate_chemistry(
        roster,
        special_connections=special_conn,
        career_teammates_map=teammates_map,
    )

    links_data = [
        {
            "player1_name": l.player1_name,
            "player1_slot": l.player1_slot,
            "player2_name": l.player2_name,
            "player2_slot": l.player2_slot,
            "bonus_type": l.bonus_type,
            "description": l.description,
            "player_bonus": l.player_bonus,
            "team_bonus": l.team_bonus,
        }
        for l in breakdown.active_links
    ]

    roster_out = {}
    for slot, p in roster.items():
        roster_out[slot] = {
            "player_id": p.player_id,
            "name": p.name,
            "position": p.position,
            "slot": p.slot,
            "drafted_team": p.drafted_team,
            "drafted_season": p.drafted_season,
            "base_fppg": p.base_fppg,
            "chemistry_fppg": p.chemistry_fppg,
            "total_fppg": p.total_fppg,
            "applied_bonuses": p.applied_bonuses,
            "headshot_url": p.headshot_url,
            "espn_id": p.espn_id,
        }

    return web.json_response({
        "base_fppg": breakdown.base_fppg,
        "chemistry_fppg": breakdown.chemistry_fppg,
        "total_score": breakdown.total_score,
        "projected_record": breakdown.projected_record,
        "tier_badge": breakdown.tier_badge,
        "tier_name": breakdown.tier_name,
        "active_links": links_data,
        "roster": roster_out,
    })


async def api_leaderboard_get(request: web.Request) -> web.Response:
    """Returns top 10 highest-scoring rosters."""
    entries = await get_leaderboard(limit=10)
    return web.json_response({"leaderboard": entries})


async def api_leaderboard_save(request: web.Request) -> web.Response:
    """Saves completed roster to leaderboard."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    user_id = str(data.get("user_id", "web_user"))
    username = str(data.get("username", "GridironGM"))
    roster_raw = data.get("roster", {})

    roster: Dict[str, RosterPlayer] = {}
    for slot, p_data in roster_raw.items():
        if not p_data:
            continue
        roster[slot] = RosterPlayer(
            player_id=p_data["player_id"],
            name=p_data.get("name", "Unknown"),
            position=p_data.get("position", "FLX"),
            slot=slot,
            drafted_team=p_data.get("drafted_team", "KC"),
            drafted_season=int(p_data.get("drafted_season", 2020)),
            base_fppg=float(p_data.get("base_fppg", 0.0)),
            college=p_data.get("college"),
            draft_year=p_data.get("draft_year"),
            headshot_url=p_data.get("headshot_url"),
            espn_id=p_data.get("espn_id"),
        )

    player_ids = [p.player_id for p in roster.values()]
    teammates_map = await get_career_teammates_map(player_ids) if len(player_ids) >= 2 else set()
    special_conn = await get_special_connections_for_players(player_ids) if len(player_ids) >= 2 else {}

    breakdown = calculate_chemistry(roster, special_connections=special_conn, career_teammates_map=teammates_map)

    row_id = await save_to_leaderboard(
        user_id=user_id,
        username=username,
        total_score=breakdown.total_score,
        projected_record=breakdown.projected_record,
        roster=roster,
    )

    return web.json_response({
        "success": True,
        "row_id": row_id,
        "total_score": breakdown.total_score,
        "projected_record": breakdown.projected_record,
    })


# --- Static Frontend Serving ---

async def serve_index(request: web.Request) -> web.FileResponse:
    """Serves the main Activity index.html."""
    return web.FileResponse(ACTIVITY_DIR / "index.html")


async def serve_style(request: web.Request) -> web.FileResponse:
    """Serves style.css directly from root or /static."""
    return web.FileResponse(ACTIVITY_DIR / "style.css")


async def serve_app_js(request: web.Request) -> web.FileResponse:
    """Serves app.js directly from root or /static."""
    return web.FileResponse(ACTIVITY_DIR / "app.js")


async def serve_audio_js(request: web.Request) -> web.FileResponse:
    """Serves audio.js directly from root or /static."""
    return web.FileResponse(ACTIVITY_DIR / "audio.js")


async def serve_stadium_canvas_js(request: web.Request) -> web.FileResponse:
    """Serves stadium_canvas.js directly from root or /static."""
    return web.FileResponse(ACTIVITY_DIR / "stadium_canvas.js")


async def serve_cards_engine_js(request: web.Request) -> web.FileResponse:
    """Serves cards_engine.js directly from root or /static."""
    return web.FileResponse(ACTIVITY_DIR / "cards_engine.js")


def create_app() -> web.Application:
    """Constructs the aiohttp web application."""
    app = web.Application()

    # CORS / Security headers middleware
    @web.middleware
    async def cors_middleware(request: web.Request, handler):
        response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["X-Frame-Options"] = "ALLOWALL"
        return response

    app.middlewares.append(cors_middleware)

    # API routes
    app.router.add_get("/api/health", api_health)
    app.router.add_get("/api/image-proxy", api_image_proxy)
    app.router.add_get("/api/roll", api_roll)
    app.router.add_post("/api/reroll-team", api_reroll_team)
    app.router.add_post("/api/reroll-season", api_reroll_season)
    app.router.add_post("/api/search", api_search_players)
    app.router.add_post("/api/calculate", api_calculate)
    app.router.add_get("/api/leaderboard", api_leaderboard_get)
    app.router.add_post("/api/leaderboard/save", api_leaderboard_save)

    # Frontend routes (support both root and /static)
    if ACTIVITY_DIR.exists():
        app.router.add_get("/", serve_index)
        app.router.add_get("/style.css", serve_style)
        app.router.add_get("/app.js", serve_app_js)
        app.router.add_get("/audio.js", serve_audio_js)
        app.router.add_get("/stadium_canvas.js", serve_stadium_canvas_js)
        app.router.add_get("/cards_engine.js", serve_cards_engine_js)
        app.router.add_static("/static", ACTIVITY_DIR, name="static")

    return app


async def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    """Starts the aiohttp web server on the given host and port."""
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("🏈 17-0 Activity Web Server running on http://%s:%d", host, port)
    return runner


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        runner = loop.run_until_complete(start_web_server(port=port))
        logger.info("Press Ctrl+C to stop.")
        loop.run_forever()
    except KeyboardInterrupt:
        pass
