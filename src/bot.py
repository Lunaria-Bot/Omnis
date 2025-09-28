import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from src.config import DISCORD_TOKEN, GUILD_ID, REDIS_URL, LOG_LEVEL
from src.db import init_db
from src.redis_client import init_redis

# Convert LOG_LEVEL string into numeric level
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class OmnisBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("src.cogs.moderation")
        await self.load_extension("src.cogs.tickets")
        await self.load_extension("src.cogs.logs")
        await self.load_extension("src.cogs.tasks")  # background tasks cog
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        logging.info("Slash commands synced for guild %s", GUILD_ID)

bot = OmnisBot()

@bot.event
async def on_ready():
    logging.info("Connected as %s", bot.user)

async def main():
    await init_db()
    await init_redis(REDIS_URL)
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
