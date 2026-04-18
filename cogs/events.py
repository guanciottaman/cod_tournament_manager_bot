import discord
from discord.ext import commands
from discord import app_commands

import sqlite3

from db import get_db


default_placement_points = {
    "1": 15,
    "2": 12,
    "3": 10,
    "4": 8,
    "5": 6
}

def get_placement_points(event_id):
    db = get_db()
    c = db.cursor()

    c.execute("""
        SELECT position, points
        FROM placement_points
        WHERE event_id = ?
        ORDER BY position ASC
    """, (event_id,))

    rows = c.fetchall()
    db.close()

    return rows

def build_event_embed(event_id):
    db = get_db()
    c = db.cursor()

    c.execute("""
        SELECT matches_number, players_per_team, kd_mode
        FROM events_settings
        WHERE event_id = ?
    """, (event_id,))

    row = c.fetchone()

    db.close()

    matches, players, kd = (5, 4, 0) if not row else row

    placement_points = get_placement_points(event_id)

    embed = discord.Embed(
        title="Configurazione evento",
        color=discord.Color.blurple()
    )

    embed.description = (
        f"**Match:** {matches}\n"
        f"**Giocatori per team:** {players}\n"
        f"**KD Mode:** {'ON' if kd else 'OFF'}\n\n"
        f"**Punti piazzamento:**\n"
    )

    if placement_points:
        for position, points in placement_points:
            embed.description += f"{position}° posto: *{points} punti*\n"
    else:
        for position, points in default_placement_points.items():
            embed.description += f"{position}° posto: *{points} punti*\n"

    return embed

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
            db = get_db()
            c = db.cursor()
            c.execute("""INSERT INTO server_configs
                (guild_id, ranking_channel_id, members_commands_channel_id, admin_role_id)
                VALUES (?, ?, ?, ?)""",
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
        db = get_db()
        c = db.cursor()
        c.execute(
            "DELETE FROM server_configs WHERE guild_id = ?",
            (interaction.guild_id,)
        )

        db.commit()
        db.close()

        await interaction.response.edit_message(
            content="Server rimosso dal sistema con successo.",
            view=None
        )


class PlacementModal(discord.ui.Modal, title="Punti piazzamento"):

    first = discord.ui.TextInput(label="1° posto", default=default_placement_points["1"])
    second = discord.ui.TextInput(label="2° posto", default=default_placement_points["2"])
    third = discord.ui.TextInput(label="3° posto", default=default_placement_points["3"])
    fourth = discord.ui.TextInput(label="4° posto", default=default_placement_points["4"])
    fifth = discord.ui.TextInput(label="5° posto", default=default_placement_points["5"])

    def __init__(self, event_id: int, view: discord.ui.View):
        super().__init__()
        self.event_id = event_id
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        values = [
            self.first.value,
            self.second.value,
            self.third.value,
            self.fourth.value,
            self.fifth.value
        ]
        if not all(
            val.isnumeric() for val in values
        ):
            await interaction.response.send_message("Tutti i valori devono essere numeri!", ephemeral=True)
            return
        db = get_db()
        c = db.cursor()
        c.execute("DELETE FROM placement_points WHERE event_id = ?", (self.event_id,))
        for i, val in enumerate(values):
            c.execute("""
                INSERT INTO placement_points (event_id, position, points) VALUES (?, ?, ?)
            """, (self.event_id, i+1, val))
        
        db.commit()
        db.close()
        embed = build_event_embed(self.event_id)
        await interaction.response.edit_message(embed=embed, view=self.view)


class CreaEventoView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id
    """
    @discord.ui.select(
        placeholder="Inserisci il numero di lobby...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=str(i), value=str(i), description=f"Numero di lobby: {i}")
                for i in range(1, 3)
        ]
    )
    async def set_lobbies_number(self, interaction: discord.Interaction, select: discord.ui.Select):
        db = get_db()
        c = db.cursor()
        c.execute(
            "UPDATE events SET lobbies_number = ? WHERE event_id = ?",
            (int(select.values[0]), self.event_id)
        )

        db.commit()
        db.close()
        await interaction.response.defer()
    """

    @discord.ui.select(
        placeholder="Numero match",
        options=[
                discord.SelectOption(label=str(i), value=str(i))
                for i in range(4, 6)
            ],
    )
    async def set_matches(self, interaction: discord.Interaction, select: discord.ui.Select):

        db = get_db()
        c = db.cursor()
        c.execute("""
            UPDATE events_settings SET matches_number = ? WHERE event_id = ?
        """, (select.values[0], self.event_id))

        db.commit()
        db.close()

        await interaction.response.edit_message(embed=build_event_embed(self.event_id), view=self)

    @discord.ui.select(
        placeholder="Numero giocatori per squadra",
        options=[
                discord.SelectOption(label=str(i), value=str(i))
                for i in range(3, 5)
            ]
    )
    async def set_players_per_team(self, interaction: discord.Interaction, select: discord.ui.Select):
        db = get_db()
        c = db.cursor()

        c.execute("""
            UPDATE events_settings SET players_per_team = ? WHERE event_id = ?
        """, (int(select.values[0]), self.event_id))

        db.commit()
        db.close()

        await interaction.response.edit_message(embed=build_event_embed(self.event_id), view=self)
    
    @discord.ui.select(
        placeholder="KD Mode",
        options=[
            discord.SelectOption(
                label="OFF",
                description="Le lobby saranno create casualmente",
                value="0",
                emoji="❌"
            ),
            discord.SelectOption(
                label="ON",
                description="Le lobby verranno create in base al rapporto K/D",
                value="1",
                emoji="✅"    
            ),
        ]
    )
    async def set_kd_mode(self, interaction: discord.Interaction, select: discord.ui.Select):
        db = get_db()
        c = db.cursor()

        c.execute("""
            UPDATE events_settings
            SET kd_mode = ?
            WHERE event_id = ?
        """, (int(select.values[0]), self.event_id))

        db.commit()
        db.close()

        await interaction.response.edit_message(embed=build_event_embed(self.event_id), view=self)
        
    @discord.ui.button(
        label="Modifica punti piazzamento",
        style=discord.ButtonStyle.secondary
    )
    async def edit_placement_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PlacementModal(self.event_id, self))
    

    @discord.ui.button(
        label="Crea evento",
        style=discord.ButtonStyle.green,
        row=4
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = get_db()
        c = db.cursor()
        c.execute(
            "UPDATE events SET status = 'ready' WHERE event_id = ?",
            (self.event_id,)
        )
        db.commit()
        db.close()
        await interaction.response.send_message("Evento creato!", ephemeral=True)


class NomeEventoModal(discord.ui.Modal, title="Nuovo evento"):
    name = discord.ui.TextInput(label="Nome evento", placeholder="Inserisci il nome dell'evento...", max_length=40)
    async def on_submit(self, interaction: discord.Interaction):
        db = get_db()
        c = db.cursor()

        c.execute(
            "INSERT INTO events (guild_id, name, status, lobbies_number, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (interaction.guild_id, self.name.value, "draft", 0)
        )
        event_id = c.lastrowid
        c.execute("INSERT INTO events_settings (event_id) VALUES (?)", (event_id,))

        db.commit()
        db.close()
        embed = build_event_embed(event_id)
        await interaction.response.send_message(
            embed=embed,
            view=CreaEventoView(event_id),
            ephemeral=True
        )
    
class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def check_admin_role(self, interaction: discord.Interaction):
        db = get_db()
        c = db.cursor()
        c.execute("SELECT admin_role_id FROM server_configs WHERE guild_id = ?", (interaction.guild_id,))
        row = c.fetchone()
        if not row:
            return False

        admin_role_id = row[0]
        db.close()
        admin_role = interaction.guild.get_role(admin_role_id)
        return True if admin_role in interaction.user.roles and admin_role is not None else False
    

    @app_commands.command(name="setup_server", description="Imposta il bot per questo server")
    @commands.has_guild_permissions(ban_members=True)
    async def setup_server(self, interaction: discord.Interaction):
        db = get_db()
        c = db.cursor()
        c.execute("SELECT 1 FROM server_configs WHERE guild_id = ?", (interaction.guild_id,))
        exists = c.fetchone()
        if exists:
            await interaction.response.send_message("Il tuo server è già registrato!", ephemeral=True)
            return
        db.close()
        await interaction.response.send_message(view=SetupView(), ephemeral=True)

    @app_commands.command(name="elimina_config_server", description="Elimina la configurazione di questo server")
    @commands.has_guild_permissions(ban_members=True)
    async def delete_server(self, interaction: discord.Interaction):
        db = get_db()
        c = db.cursor()
        c.execute("SELECT 1 FROM server_configs WHERE guild_id = ?", (interaction.guild_id,))
        exists = c.fetchone()
        if not exists:
            await interaction.response.send_message("Il tuo server non è registrato!", ephemeral=True)
            return
        db.close()
        await interaction.response.send_message(view=DeleteServerView(), ephemeral=True)

    @app_commands.command(name="crea_evento", description="Crea un nuovo evento")
    async def crea_evento(self, interaction: discord.Interaction):
        if not(await self.check_admin_role(interaction) or interaction.user.id == 646421185692958730):
            await interaction.response.send_message("Non hai il ruolo necessario a creare un nuovo evento!", ephemeral=True)
            return
        await interaction.response.send_modal(NomeEventoModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))