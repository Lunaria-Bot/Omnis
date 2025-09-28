import discord
from discord.ext import commands
from discord import app_commands
from src.db import pool
from src.redis_client import rds
from src.config import GUILD_ID

class TicketsView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        lock_key = f"lock:ticket:{guild_id}:{user_id}"
        if not await rds().set(lock_key, "1", nx=True, ex=10):
            return await interaction.response.send_message("Création déjà en cours. Patiente un instant.", ephemeral=True)

        cached = await rds().get(f"ticket:user:{guild_id}:{user_id}")
        if cached:
            return await interaction.response.send_message(f"Tu as déjà un ticket: <#{cached}>", ephemeral=True)

        async with pool().acquire() as conn:
            cfg = await conn.fetchrow("SELECT ticket_category_id, staff_role_id FROM guild_config WHERE guild_id=$1", guild_id)
        if not cfg or not cfg["ticket_category_id"]:
            return await interaction.response.send_message("Catégorie des tickets non configurée.", ephemeral=True)

        category = interaction.guild.get_channel(cfg["ticket_category_id"])
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message("Catégorie invalide.", ephemeral=True)

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
            reason="Ouverture de ticket"
        )

        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO tickets (guild_id, user_id, channel_id, status) VALUES ($1,$2,$3,$4)",
                guild_id, user_id, channel.id, "open"
            )
        await rds().set(f"ticket:user:{guild_id}:{user_id}", str(channel.id))

        await interaction.response.send_message(f"Ticket créé: {channel.mention}", ephemeral=True)
        await channel.send(f"{interaction.user.mention} Explique ton problème. Un membre du staff arrive.")

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.view = TicketsView(timeout=None)

    @app_commands.command(name="setup_tickets", description="Publie le bouton de création de tickets")
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)
        await channel.send("Besoin d'aide ? Ouvre un ticket :", view=self.view)
        await interaction.response.send_message("Bouton publié.", ephemeral=True)

    @app_commands.command(name="set_ticket_category", description="Définir la catégorie des tickets")
    async def set_ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO guild_config (guild_id, ticket_category_id) VALUES ($1,$2) "
                "ON CONFLICT (guild_id) DO UPDATE SET ticket_category_id=EXCLUDED.ticket_category_id",
                interaction.guild_id, category.id
            )
        await interaction.response.send_message(f"Catégorie des tickets: {category.name}", ephemeral=True)

    @app_commands.command(name="set_staff_role", description="Définir le rôle staff des tickets")
    async def set_staff_role(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)
        async with pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO guild_config (guild_id, staff_role_id) VALUES ($1,$2) "
                "ON CONFLICT (guild_id) DO UPDATE SET staff_role_id=EXCLUDED.staff_role_id",
                interaction.guild_id, role.id
            )
        await interaction.response.send_message(f"Rôle staff défini: {role.name}", ephemeral=True)

    @app_commands.command(name="close_ticket", description="Fermer le ticket courant")
    async def close_ticket(self, interaction: discord.Interaction):
        async with pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id FROM tickets WHERE guild_id=$1 AND channel_id=$2 AND status='open'",
                interaction.guild_id, interaction.channel_id
            )
        if not row:
            return await interaction.response.send_message("Ce salon n’est pas un ticket ouvert.", ephemeral=True)
        if interaction.user.id != row["user_id"] and not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Permission insuffisante.", ephemeral=True)

        async with pool().acquire() as conn:
            await conn.execute("UPDATE tickets SET status='closed', closed_at=NOW() WHERE id=$1", row["id"])
        await rds().delete(f"ticket:user:{interaction.guild_id}:{row['user_id']}")

        await interaction.response.send_message("Ticket fermé. Suppression du salon dans 10 secondes.", ephemeral=True)
        await interaction.channel.send("Archivage…")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=10))
        try:
            await interaction.channel.delete(reason="Ticket fermé")
        except discord.Forbidden:
            pass

async def setup(bot: commands.Bot):
    cog = Tickets(bot)
    await bot.add_cog(cog)
    bot.add_view(cog.view)  # Vue persistante au redémarrage
    bot.tree.add_command(cog.setup_tickets, guild=discord.Object(id=GUILD_ID))
    bot.tree.add_command(cog.set_ticket_category, guild=discord.Object(id=GUILD_ID))
    bot.tree.add_command(cog.set_staff_role, guild=discord.Object(id=GUILD_ID))
    bot.tree.add_command(cog.close_ticket, guild=discord.Object(id=GUILD_ID))
