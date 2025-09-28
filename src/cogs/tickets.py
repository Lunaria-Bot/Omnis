import discord
from discord.ext import commands
from discord import app_commands
from src.db import pool
from src.redis_client import rds
from src.config import GUILD_ID

class TicketsView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Open a ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        lock_key = f"lock:ticket:{guild_id}:{user_id}"
        if not await rds().set(lock_key, "1", nx=True, ex=10):
            return await interaction.response.send_message("Ticket creation already in progress. Please wait.", ephemeral=True)

        cached = await rds().get(f"ticket:user:{guild_id}:{user_id}")
        if cached:
            return await interaction.response.send_message(f"You already have a ticket: <#{cached}>", ephemeral=True)

        async with pool().acquire() as conn:
            cfg = await conn.fetchrow("SELECT ticket_category_id, staff_role_id FROM guild_config WHERE guild_id=$1", guild_id)
        if not cfg or not cfg["ticket_category_id"]:
            return await interaction.response.send_message("Ticket category not configured.", ephemeral=True)

        category = interaction.guild.get_channel(cfg["ticket_category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message("Invalid category.", ephemeral=True)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if cfg["staff_role_id"]:
            role = interaction.guild.get_role(cfg["staff_role_id"])
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            reason="Ticket opened"
        )

        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO tickets (guild_id, user_id, channel_id, status) VALUES ($1,$2,$3,$4)",
                guild_id, user_id, channel.id, "open"
            )
        await rds().set(f"ticket:user:{guild_id}:{user_id}", str(channel.id))

        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
        await channel.send(f"{interaction.user.mention} Please describe your issue. A staff member will assist you shortly.")

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.view = TicketsView(timeout=None)

    @app_commands.command(name="setup_tickets", description="Post the ticket creation button")
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        await channel.send("Need help? Open a ticket:", view=self.view)
        await interaction.response.send_message("Ticket button posted.", ephemeral=True)

    @app_commands.command(name="set_ticket_category", description="Set the ticket category")
    async def set_ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("You don't have permission.", ephemeral=True)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO guild_config (guild_id, ticket_category_id) VALUES ($1,$2) "
                "ON CONFLICT (guild_id) DO UPDATE SET ticket_category_id=EXCLUDED.ticket_category_id",
                interaction.guild_id, category.id
            )
        await interaction.response.send_message(f"Ticket category set to: {category.name}", ephemeral=True)

    @app_commands.command(name="set_staff_role", description="Set the staff role for tickets")
    async def set_staff_role(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message
