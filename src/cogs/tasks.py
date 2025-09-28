import asyncio
import itertools
import logging
import discord
from discord.ext import commands

log = logging.getLogger("cog-tasks")

# Liste des statuts qui vont tourner en boucle
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
        # On ne lance les tâches qu'une seule fois
        if not self._status_task:
            self._status_task = asyncio.create_task(self.cycle_status())
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self.heartbeat())
        log.info("✅ Background tasks launched")

    async def cycle_status(self):
        """Change le statut du bot toutes les 5 minutes."""
        for activity in itertools.cycle(STATUSES):
            try:
                await self.bot.change_presence(activity=activity, status=discord.Status.online)
                log.info(f"Presence changed to: {activity.name}")
            except Exception:
                log.exception("Failed to change presence")
            await asyncio.sleep(300)  # 5 minutes

    async def heartbeat(self):
        """Tâche de heartbeat pour vérifier que le bot tourne bien."""
        while True:
            log.debug("💓 Heartbeat OK")
            await asyncio.sleep(60)  # toutes les minutes

async def setup(bot: commands.Bot):
    await bot.add_cog(Tasks(bot))
