import discord
from discord import app_commands
from discord.ext import commands
from db import pool
from redis_client import rds
from config import GUILD_ID

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _has_mod_perms(self, m: discord.Member) -> bool:
        p = m.guild_permissions
        return p.kick_members or p.ban_members or p.manage_roles

    @app_commands.command(name="warn", description="Avertir un membre")
    @app_commands.describe(member="Membre à avertir", reason="Raison")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
        if not self._has_mod_perms(interaction.user):
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)

        key = f"rl:mod:{interaction.guild_id}:{interaction.user.id}"
        ttl = await rds().ttl(key)
        if ttl and ttl > 0:
            return await interaction.response.send_message("Trop d’actions, réessaie bientôt.", ephemeral=True)
        await rds().setex(key, 5, "1")

        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO moderation_cases (guild_id, target_id, moderator_id, action, reason) VALUES ($1,$2,$3,$4,$5)",
                interaction.guild_id, member.id, interaction.user.id, "warn", reason
            )

        embed = discord.Embed(title="Avertissement", description=f"{member.mention} averti.", color=discord.Color.gold())
        embed.add_field(name="Raison", value=reason, inline=False)
        embed.set_footer(text=f"Par {interaction.user}")
        await interaction.response.send_message(embed=embed)

        try:
            await member.send(f"Tu as reçu un avertissement sur {interaction.guild.name} : {reason}")
        except discord.Forbidden:
            pass

    @app_commands.command(name="kick", description="Expulser un membre")
    @app_commands.describe(member="Membre à expulser", reason="Raison")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
        if not self._has_mod_perms(interaction.user):
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)
        await member.kick(reason=reason)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO moderation_cases (guild_id, target_id, moderator_id, action, reason) VALUES ($1,$2,$3,$4,$5)",
                interaction.guild_id, member.id, interaction.user.id, "kick", reason
            )
        await interaction.response.send_message(f"{member} expulsé. Raison: {reason}")

    @app_commands.command(name="ban", description="Bannir un membre")
    @app_commands.describe(member="Membre à bannir", reason="Raison")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
        if not self._has_mod_perms(interaction.user):
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)
        await member.ban(reason=reason, delete_message_days=0)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO moderation_cases (guild_id, target_id, moderator_id, action, reason) VALUES ($1,$2,$3,$4,$5)",
                interaction.guild_id, member.id, interaction.user.id, "ban", reason
            )
        await interaction.response.send_message(f"{member} banni. Raison: {reason}")

    @app_commands.command(name="cases", description="Voir les derniers cas d'un membre")
    async def cases(self, interaction: discord.Interaction, member: discord.Member):
        async with pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, action, reason, created_at FROM moderation_cases WHERE guild_id=$1 AND target_id=$2 ORDER BY created_at DESC LIMIT 10",
                interaction.guild_id, member.id
            )
        if not rows:
            return await interaction.response.send_message("Aucun cas.", ephemeral=True)

        embed = discord.Embed(title=f"Cas de {member}", color=discord.Color.orange())
        for r in rows:
            embed.add_field(name=f"#{r['id']} • {r['action']}", value=f"{r['created_at'].strftime('%Y-%m-%d')} — {r['reason']}", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    cog = Moderation(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.warn, guild=discord.Object(id=GUILD_ID))
    bot.tree.add_command(cog.kick, guild=discord.Object(id=GUILD_ID))
    bot.tree.add_command(cog.ban, guild=discord.Object(id=GUILD_ID))
    bot.tree.add_command(cog.cases, guild=discord.Object(id=GUILD_ID))
