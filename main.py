"""
Main entry point for Prayer Notice Discord Bot.
Handles bot initialization, cog loading, slash command synchronization,
and scheduler lifecycle.
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

import discord
from discord.ext import commands

from core.database import Database
from core.scheduler import PrayerScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("prayerbot")


class PrayerBot(commands.Bot):
    def __init__(self, db_path: str = "data/prayerbot.db"):
        intents = discord.Intents.default()
        allowed_mentions = discord.AllowedMentions(everyone=True, roles=True, users=True)
        # Slash commands don't require privileged message_content intent
        super().__init__(command_prefix="!", intents=intents, allowed_mentions=allowed_mentions)
        self.db = Database(db_path)
        self.scheduler = PrayerScheduler(self, self.db)

    async def setup_hook(self):
        """Called automatically before bot connects to Discord gateway."""
        # 1. Initialize SQLite database
        logger.info("Initializing database...")
        await self.db.init()

        # 2. Load cogs
        cogs = ["cogs.settings", "cogs.prayers"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded extension: {cog}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog}: {e}", exc_info=True)

        # 3. Sync Slash Commands globally
        logger.info("Syncing slash commands with Discord...")
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} application commands.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}", exc_info=True)

        # 4. Start background scheduler
        self.scheduler.start()

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds.")

        # Set presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="مواقيت الصلاة | /today",
        )
        await self.change_presence(activity=activity)

    async def close(self):
        logger.info("Shutting down bot...")
        self.scheduler.stop()
        await super().close()


def main():
    # Load .env file
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token or token.strip() == "your_discord_bot_token_here":
        logger.error(
            "ERROR: DISCORD_TOKEN is missing or not configured!\n"
            "Please copy .env.example to .env and insert your Discord Bot Token."
        )
        sys.exit(1)

    db_path = os.getenv("DATABASE_PATH", "data/prayerbot.db")

    bot = PrayerBot(db_path=db_path)
    bot.run(token)


if __name__ == "__main__":
    main()
