import sys
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
import pytest

# Add package base directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent / "17_0_bot"
sys.path.insert(0, str(BASE_DIR))

from web_server import create_app


@pytest.mark.asyncio
async def test_web_api_endpoints():
    app = create_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        # 1. Test Health
        resp = await client.get("/api/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"

        # 2. Test Roll
        resp = await client.get("/api/roll")
        assert resp.status == 200
        data = await resp.json()
        assert "team" in data
        assert "season" in data
        assert "players" in data
        assert isinstance(data["players"], list)

        # 3. Test Reroll Team
        resp = await client.post(
            "/api/reroll-team",
            json={"season": 2020, "current_team": "KC", "positions": ["QB", "RB"]},
        )
        assert resp.status == 200
        data = await resp.json()
        assert "team" in data
        assert data["season"] == 2020

        # 4. Test Reroll Season
        resp = await client.post(
            "/api/reroll-season",
            json={"team": "KC", "current_season": 2020, "positions": ["WR", "TE"]},
        )
        assert resp.status == 200
        data = await resp.json()
        assert "season" in data
        assert data["team"] == "KC"

        # 5. Test Calculate Chemistry
        roster_payload = {
            "roster": {
                "QB": {
                    "player_id": "00-0019596",
                    "name": "Tom Brady",
                    "position": "QB",
                    "drafted_team": "NE",
                    "drafted_season": 2011,
                    "base_fppg": 24.5,
                    "college": "Michigan",
                    "draft_year": 2000,
                },
                "TE": {
                    "player_id": "00-0027656",
                    "name": "Rob Gronkowski",
                    "position": "TE",
                    "drafted_team": "NE",
                    "drafted_season": 2011,
                    "base_fppg": 20.1,
                    "college": "Arizona",
                    "draft_year": 2010,
                },
            }
        }
        resp = await client.post("/api/calculate", json=roster_payload)
        assert resp.status == 200
        calc_data = await resp.json()
        assert calc_data["base_fppg"] == 44.6
        assert calc_data["chemistry_fppg"] > 0
        assert calc_data["total_score"] > calc_data["base_fppg"]

        # 6. Test Leaderboard Get
        resp = await client.get("/api/leaderboard")
        assert resp.status == 200
        lb_data = await resp.json()
        assert "leaderboard" in lb_data
        assert isinstance(lb_data["leaderboard"], list)

        # 7. Test Static Index serving
        resp = await client.get("/")
        assert resp.status == 200
        text = await resp.text()
        assert "17-0" in text

    finally:
        await client.close()
