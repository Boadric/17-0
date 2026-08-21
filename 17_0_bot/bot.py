import asyncio
import logging
import os
import sys
from pathlib import Path
import discord
from discord.ext import commands

# Ensure package directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from config import APPLICATION_ID, DB_PATH, DISCORD_TOKEN, GUILD_ID
    from web_server import start_web_server
except (ImportError, ValueError):
    from .config import APPLICATION_ID, DB_PATH, DISCORD_TOKEN, GUILD_ID
    from .web_server import start_web_server

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("17_0_bot")


class SeventeenZeroBot(commands.Bot):
    """Custom Bot class for 17-0 Game Bot & Activity Server."""

    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=int(APPLICATION_ID) if APPLICATION_ID and APPLICATION_ID.isdigit() else None,
            help_command=None,
        )
        self._synced = False
        self.web_runner = None

    async def setup_hook(self):
        """Called asynchronously before the bot logs in to load cogs and start web server."""
        logger.info("Initializing 17-0 Bot extensions...")

        # 1. Load Cogs
        cog_path = BASE_DIR / "cogs"
        for file in cog_path.glob("*.py"):
            if not file.name.startswith("__"):
                cog_name = f"cogs.{file.stem}"
                try:
                    await self.load_extension(cog_name)
                    logger.info("Loaded cog: %s", cog_name)
                except Exception as e:
                    try:
                        await self.load_extension(f"17_0_bot.cogs.{file.stem}")
                        logger.info("Loaded cog: 17_0_bot.cogs.%s", file.stem)
                    except Exception as ex:
                        logger.error("Failed to load extension %s: %s", cog_name, ex, exc_info=True)

        # 2. Start Web & Activity API Server concurrently
        port = int(os.getenv("PORT", "8080"))
        try:
            self.web_runner = await start_web_server(port=port)
            logger.info("🏈 17-0 Activity Web Server online on port %d", port)
        except Exception as e:
            logger.warning("Could not start Web Server: %s", e)

    async def on_ready(self):
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        logger.info("Database path: %s", DB_PATH)

        if not self._synced:
            try:
                if GUILD_ID:
                    guild = discord.Object(id=GUILD_ID)
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    logger.info("Synced %d slash commands to guild %d.", len(synced), GUILD_ID)
                else:
                    synced = await self.tree.sync()
                    logger.info("Synced %d global slash commands.", len(synced))
                self._synced = True
            except Exception as e:
                logger.warning("Could not sync slash commands: %s", e)

        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="/17-0 play | 🏈 17-0 Game",
        )
        await self.change_presence(activity=activity)
        logger.info("🏈 17-0 Bot is online and ready for drafting!")

    async def close(self):
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().close()


def main():
    token = DISCORD_TOKEN
    if not token:
        logger.error(
            "DISCORD_TOKEN is missing! Please create a .env file with your Discord Bot Token:\n"
            "DISCORD_TOKEN=your_token_here\n"
            "or pass it as an environment variable."
        )
        sys.exit(1)

    bot = SeventeenZeroBot()
    bot.run(token)


if __name__ == "__main__":
    main()
