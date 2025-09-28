import asyncio
import itertools
import logging
import discord
from discord.ext import commands
from discord import app_commands

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
    cog = Tasks(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.status, guild=discord.Object(id=bot.guilds[0].id))  # sync in guild
