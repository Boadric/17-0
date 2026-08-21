# 🏈 17-0 Discord Bot (NFL Draft & Chemistry Strategy Game)

A full-featured Discord bot replicating the viral mobile fantasy draft game **"17-0"**. Players roll random historical NFL franchises and seasons (1999–2024), view the real-life players and fantasy points scored on that roster, draft offensive weapons into a 7-slot lineup, trigger stacking **Chemistry Link bonuses**, and attempt to achieve an undefeated **17-0 regular season record** based on real PPR Fantasy Points Per Game (FPPG).

---

## 🌟 Key Features

1. **Available Weapons Board & 1-Click Dropdown Drafting**:
   - Displays all historical offensive skill players (`QB`, `RB`, `WR`, `TE`) on that franchise and season with their exact real-life **PPR FPPG**, **Alma Mater / College**, and **Draft Year / UDFA** status.
   - Dynamic **SelectMenu Dropdown**: Draft any player with 1 click!
   - **Position Filter Buttons**: Filter available weapons instantly by `[All]`, `[QB]`, `[RB]`, `[WR]`, or `[TE]`.
   - **Custom Search (`🔍`)**: Search for deeper bench players by name if desired.

2. **Historical NFL Dataset (1999–2024)**:
   - Over 5,000 players and 19,000+ historical season stat lines seeded via `nfl_data_py`.
   - Real-life PPR fantasy calculation ($0.04$ pass yd, $4$ pass TD, $-2$ INT, $0.1$ rush yd, $6$ rush TD, $1.0$ rec PPR, $0.1$ rec yd, $6$ rec TD, $-2$ fumble lost).

3. **Stacking Chemistry Link Matrix**:
   - ⚡ **Same Team & Season**: `+2.0` FPPG to both players (`+4.0` team total) if drafted from the exact same team and year.
   - 🤝 **Past Teammates**: `+1.0` FPPG to both (`+2.0` team total) if they were ever teammates in their careers *(mutually exclusive with Same Team in current season)*.
   - 🎓 **Same College (Alma Mater)**: `+2.0` FPPG to both (`+4.0` team total) if they attended the same university.
   - 📅 **Same Draft Class**: `+1.0` FPPG to both (`+2.0` team total) if drafted in the same NFL Draft year.
   - 🌟 **Elite Connection**: `+1.0` FPPG to both (`+2.0` team total) for iconic tandems (e.g. *Burrow & Chase*, *Brees & Graham*).
   - 👑 **Legendary Connection**: `+2.0` FPPG to both (`+4.0` team total) for all-time great duos (e.g. *Brady & Gronk*, *Mahomes & Kelce*, *Manning & Harrison*).

4. **Turn Flow & Rerolls**:
   - 7 total drafting rounds.
   - 1 Team Reroll (`🎲`) and 1 Year Reroll (`📅`) per game session.
   - Dynamic slot picker when a player is eligible for multiple positions (e.g., WR1, WR2, or FLX).

5. **Hall of Fame Leaderboard**:
   - SQLite persistent storage with WAL mode enabled.
   - Saves final rosters, top scores, and projected record badges.

---

## 📁 Project Structure

```
.
├── 17_0_bot/
│   ├── bot.py                  # Bot entry point, slash command registration
│   ├── config.py               # Tokens, database path, NFL team mappings & colors
│   ├── database.py             # aiosqlite non-blocking DB helpers (WAL mode)
│   ├── db_seed.py              # NFL data ETL pipeline & special connections
│   ├── cogs/
│   │   └── game.py             # Game state machine, slash commands & UI Views/Modals
│   └── utils/
│       └── scoring.py          # Chemistry matrix evaluation & record projection
├── tests/
│   ├── test_scoring.py         # Unit tests for scoring & chemistry matrix
│   ├── test_database.py        # Unit tests for database queries & helpers
│   ├── test_game_flow.py       # Unit tests for turn flow & slot assignment
│   └── test_integration.py     # Integration tests against live database
├── run_bot.py                  # Direct runner script
├── start_bot.bat               # Windows batch launcher
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.11+
- Discord Bot credentials from the [Discord Developer Portal](https://discord.com/developers/applications)

### 2. Run the Bot
Double-click **`start_bot.bat`** or run:
```cmd
python run_bot.py
```

### 3. Invite the Bot to Your Discord Server
Click the OAuth2 invite link:
👉 **[Invite 17-0 Bot](https://discord.com/oauth2/authorize?client_id=1540222119697322004&scope=bot%20applications.commands&permissions=277025778752)**

---

## 🎮 Discord Slash Commands

| Command | Description |
|---|---|
| `/17-0 play` | Starts a new 7-round single-player 17-0 draft game session. |
| `/17-0 leaderboard` | Displays the top 10 highest-scoring rosters and record badges. |
| `/17-0 rules` | Explains scoring formulas, roster slots, rerolls, and chemistry bonuses. |

---

## 🏆 Projected Regular Season Record Tiers

| FPPG Score Range | Projected Record | Tier Badge & Title |
|---|---|---|
| $\ge 160.0$ | **17-0** | 🏆 Undefeated Champion |
| $145.0 - 159.9$ | **15-2** to **16-1** | 💍 Super Bowl Contender |
| $130.0 - 144.9$ | **12-5** to **14-3** | 🔒 Playoff Lock |
| $115.0 - 129.9$ | **9-8** to **11-6** | 🫧 Wild Card Bubble |
| $< 115.0$ | $\le$ **8-9** | 🎟️ Draft Lottery Bound |
