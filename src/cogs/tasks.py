import asyncio
import itertools
import logging
import discord
from discord.ext import commands
from discord import app_commands
from src.config import GUILD_ID  # bind slash command to your guild

log = logging.getLogger("cog-tasks")

STATUSES = [
    discord.Activity(type=discord.ActivityType.watching, name="Lilac 🌸"),
    discord.Activity(type=discord.ActivityType.playing, name="Silksong 🪡"),
    discord.Activity(type=discord.ActivityType.listening, name="to Chase Atlantic 🌹"),
]

class Tasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._status_task = None
        self._heartbeat_task = None

    @commands.Cog.listener()
    async def on_ready(self):
        # Start background tasks once when the bot is ready
        if not self._status_task:
            self._status_task = asyncio.create_task(self.cycle_status())
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self.heartbeat())
        log.info("✅ Background tasks launched")

    async def cycle_status(self):
        """Rotate the bot's status every 5 minutes."""
        for activity in itertools.cycle(STATUSES):
            try:
                await self.bot.change_presence(activity=activity, status=discord.Status.online)
                log.info(f"Presence changed to: {activity.name}")
            except Exception:
                log.exception("Failed to change presence")
            await asyncio.sleep(300)

    async def heartbeat(self):
        """Heartbeat task to confirm the bot is alive."""
        while True:
            log.debug("💓 Heartbeat OK")
            await asyncio.sleep(60)

    @app_commands.command(name="status", description="Manually set the bot's status")
    @app_commands.describe(type="Type of activity", text="Status text")
    @app_commands.guilds(GUILD_ID)  # bind this command to your guild to avoid global registration timing issues
    async def status(self, interaction: discord.Interaction, type: str, text: str):
        """Slash command to manually set a custom status."""
        mapping = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing,
        }
        activity_type = mapping.get(type.lower())
        if not activity_type:
            return await interaction.response.send_message(
                "Invalid type. Use: playing, watching, listening, competing.", ephemeral=True
            )

        activity = discord.Activity(type=activity_type, name=text)
        await self.bot.change_presence(activity=activity, status=discord.Status.online)
        await interaction.response.send_message(f"✅ Status set to {type} {text}", ephemeral=True)

async def setup(bot: commands.Bot):
    # Just add the cog; command registration will be handled by the bot's tree sync
    await bot.add_cog(Tasks(bot))
