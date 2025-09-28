import discord
from discord import app_commands
from discord.ext import commands
from src.db import pool
from src.redis_client import rds
from src.config import GUILD_ID

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _has_mod_perms(self, member: discord.Member) -> bool:
        perms = member.guild_permissions
        return perms.kick_members or perms.ban_members or perms.manage_roles

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Reason")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self._has_mod_perms(interaction.user):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)

        key = f"rl:mod:{interaction.guild_id}:{interaction.user.id}"
        ttl = await rds().ttl(key)
        if ttl and ttl > 0:
            return await interaction.response.send_message("Too many actions, try again later.", ephemeral=True)
        await rds().setex(key, 5, "1")

        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO moderation_cases (guild_id, target_id, moderator_id, action, reason) VALUES ($1,$2,$3,$4,$5)",
                interaction.guild_id, member.id, interaction.user.id, "warn", reason
            )

        embed = discord.Embed(title="Warning", description=f"{member.mention} has been warned.", color=discord.Color.gold())
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Issued by {interaction.user}")
        await interaction.response.send_message(embed=embed)

        try:
            await member.send(f"You have been warned in {interaction.guild.name}: {reason}")
        except discord.Forbidden:
            pass

    @app_commands.command(name="kick", description="Kick a member")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self._has_mod_perms(interaction.user):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        await member.kick(reason=reason)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO moderation_cases (guild_id, target_id, moderator_id, action, reason) VALUES ($1,$2,$3,$4,$5)",
                interaction.guild_id, member.id, interaction.user.id, "kick", reason
            )
        await interaction.response.send_message(f"{member} has been kicked. Reason: {reason}")

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self._has_mod_perms(interaction.user):
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        await member.ban(reason=reason, delete_message_days=0)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO moderation_cases (guild_id, target_id, moderator_id, action, reason) VALUES ($1,$2,$3,$4,$5)",
                interaction.guild_id, member.id, interaction.user.id, "ban", reason
            )
        await interaction.response.send_message(f"{member} has been banned. Reason: {reason}")

    @app_commands.command(name="cases", description="View recent cases for a member")
    async def cases(self, interaction: discord.Interaction, member: discord.Member):
        async with pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, action, reason, created_at FROM moderation_cases WHERE guild_id=$1 AND target_id=$2 ORDER BY created_at DESC LIMIT 10",
                interaction.guild_id, member.id
            )
        if not rows:
            return await interaction.response.send_message("No cases found.", ephemeral=True)

        embed = discord.Embed(title=f"Cases for {member}", color=discord.Color.orange())
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
