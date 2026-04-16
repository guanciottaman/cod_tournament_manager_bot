import discord
from discord.ext import commands
from discord import app_commands

import sqlite3


class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ranking_channel: discord.TextChannel = None
        self.send_matches_channel: discord.TextChannel = None
        self.admin_role: discord.Role = None

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per le classifiche",
        min_values=1,
        max_values=1,
        row=0
    )
    async def select_ranking_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.ranking_channel = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Seleziona il canale per i comandi dei membri",
        min_values=1,
        max_values=1,
        row=1
    )
    async def select_members_commands_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.send_matches_channel = select.values[0]
        await interaction.response.defer()
    
    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Seleziona il ruolo che potrà dare penalità o gestire eventi",
        min_values=1,
        max_values=1,
        row=2
    )
    async def select_admin_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.admin_role = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(
        label="Conferma",
        style=discord.ButtonStyle.green,
        row=3
    )
    async def confirm_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not all([
            self.ranking_channel,
            self.send_matches_channel,
            self.admin_role
        ]):
            await interaction.response.send_message("Tutte le opzioni devono essere inserite!", ephemeral=True)
            return
        
        try:
            db = sqlite3.connect("db.sqlite3")
            c = db.cursor()
            c.execute("INSERT INTO server_configs VALUES(?, ?, ?, ?)",
                    (interaction.guild_id, self.ranking_channel.id, self.send_matches_channel.id, self.admin_role.id))
            db.commit()
        except sqlite3.IntegrityError:
            await interaction.response.send_message("Il tuo server è già registrato!", ephemeral=True)
            return
        finally:
            db.close()
        await interaction.response.send_message("Il tuo server è stato registrato con successo!", ephemeral=True)


class DeleteServerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(
        label="❌ Annulla",
        style=discord.ButtonStyle.gray
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Operazione annullata.",
            view=None
        )

    @discord.ui.button(
        label="🗑 Conferma eliminazione",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = sqlite3.connect("db.sqlite3")
        c = db.cursor()
        c.execute(
            "DELETE FROM server_configs WHERE server_id = ?",
            (interaction.guild_id,)
        )

        db.commit()
        db.close()

        await interaction.response.edit_message(
            content="Server rimosso dal sistema con successo.",
            view=None
        )
        


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command(name="setup_server", description="Imposta il bot per questo server")
    @commands.has_guild_permissions(ban_members=True)
    async def setup_server(self, interaction: discord.Interaction):
        db = sqlite3.connect("db.sqlite3")
        c = db.cursor()
        c.execute("SELECT 1 FROM server_configs WHERE server_id = ?", (interaction.guild_id,))
        exists = c.fetchone()
        if exists:
            await interaction.response.send_message("Il tuo server è già registrato!", ephemeral=True)
            return
        db.close()
        await interaction.response.send_message(view=SetupView(), ephemeral=True)

    @app_commands.command(name="elimina_config_server", description="Elimina la configurazione di questo server")
    @commands.has_guild_permissions(ban_members=True)
    async def delete_server(self, interaction: discord.Interaction):
        db = sqlite3.connect("db.sqlite3")
        c = db.cursor()
        c.execute("SELECT 1 FROM server_configs WHERE server_id = ?", (interaction.guild_id,))
        exists = c.fetchone()
        if not exists:
            await interaction.response.send_message("Il tuo server non è registrato!", ephemeral=True)
            return
        db.close()
        await interaction.response.send_message(view=DeleteServerView(), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))