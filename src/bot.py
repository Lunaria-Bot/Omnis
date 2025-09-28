import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from config import DISCORD_TOKEN, GUILD_ID, PG_DSN, REDIS_URL, LOG_LEVEL
from db import init_db
from redis_client import init_redis

logging.basicConfig(level=getattr(logging, LOG_LEVEL))
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class OmnisBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.tickets")
        await self.load_extension("cogs.logs")
        # Sync guild-only pour éviter le délai global
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        logging.info("Slash commands synced sur la guilde %s", GUILD_ID)

bot = OmnisBot()

@bot.event
async def on_ready():
    logging.info("Connecté en tant que %s", bot.user)

async def main():
    await init_db(PG_DSN)
    await init_redis(REDIS_URL)
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
