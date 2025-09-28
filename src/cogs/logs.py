import discord
import json
from discord.ext import commands
from discord import app_commands
from db import pool
from redis_client import rds
from config import GUILD_ID

class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_log_channel(self, guild_id: int):
        async with pool().acquire() as conn:
            row = await conn.fetchrow("SELECT log_channel_id FROM guild_config WHERE guild_id=$1", guild_id)
        if row and row["log_channel_id"]:
            return self.bot.get_channel(row["log_channel_id"])
        return None

    @app_commands.command(name="set_log_channel", description="Définir le salon de logs")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO guild_config (guild_id, log_channel_id) VALUES ($1,$2) "
                "ON CONFLICT (guild_id) DO UPDATE SET log_channel_id=EXCLUDED.log_channel_id",
                interaction.guild_id, channel.id
            )
        await interaction.response.send_message(f"Salon de logs: {channel.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        payload = {
            "author_id": message.author.id,
            "channel_id": message.channel.id,
            "content": message.content,
        }
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO audit_logs (guild_id, event_type, payload) VALUES ($1,$2,$3::jsonb)",
                message.guild.id, "message_delete", json.dumps(payload)
            )
        await rds().lpush(f"logs:last:{message.guild.id}", json.dumps(payload))
        chan = await self._get_log_channel(message.guild.id)
        if chan:
            embed = discord.Embed(title="Message supprimé", color=discord.Color.red())
            embed.add_field(name="Auteur", value=f"<@{message.author.id}>")
            embed.add_field(name="Salon", value=f"<#{message.channel.id}>")
            embed.add_field(name="Contenu", value=message.content or "(embed/attachments)", inline=False)
            await chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        payload = {"member_id": member.id}
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO audit_logs (guild_id, event_type, payload) VALUES ($1,$2,$3::jsonb)",
                member.guild.id, "member_join", json.dumps(payload)
            )
        chan = await self._get_log_channel(member.guild.id)
        if chan:
            await chan.send(f"Arrivée: {member.mention}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        payload = {"member_id": member.id}
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO audit_logs (guild_id, event_type, payload) VALUES ($1,$2,$3::jsonb)",
                member.guild.id, "member_leave", json.dumps(payload)
            )
        chan = await self._get_log_channel(member.guild.id)
        if chan:
            await chan.send(f"Départ: {member.mention}")

async def setup(bot: commands.Bot):
    cog = Logs(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.set_log_channel, guild=discord.Object(id=GUILD_ID))
