import discord
from discord.ext import commands
from discord import app_commands

from cogs.events import build_event_selector
from services.team_service import *
from services.event_service import *
from services.server_service import *


class RegistraTeamModal(discord.ui.Modal, title="Registra il tuo team"):
    nome_team = discord.ui.TextInput(
        label="Nome team",
        placeholder="Inserisci il nome del tuo team...",
        min_length=3,
        max_length=20
    )
    capoteam = discord.ui.TextInput(
        label="Nome capoteam",
        placeholder="Inserisci il tuo username di CoD (compreso il numero)...",
        min_length=5,
        max_length=20
    )
    def __init__(self, event_id: int, members_number: int):
        super().__init__()
        self.event_id = event_id
        self.members_number = members_number

        self.inputs: list[discord.ui.TextInput] = []
        for i in range(self.members_number-1):

            inp = discord.ui.TextInput(
                label=f"Giocatore {i+2}",
                placeholder=f"Inserisci l'username di CoD del giocatore {i+2} (compreso il numero)...",
                min_length=5,
                max_length=20
            )

            self.inputs.append(inp)
            self.add_item(inp)
    
    async def on_submit(self, interaction: discord.Interaction):
        names = [self.capoteam.value]
        for inp in self.inputs:
            names.append(inp.value)
        try:
            await insert_teams(self.event_id, self.nome_team.value, interaction.user.id, names)
        except ValueError:
            await interaction.response.send_message("Hai già iscritto un team a questo evento!", ephemeral=True)
            return
        await interaction.response.send_message("Hai iscritto il tuo team all'evento con successo!", ephemeral=True)


class Teams(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
    
    @app_commands.command(name="registra_team", description="Registra il tuo team a un evento")
    async def registra_team(self, interaction: discord.Interaction):
        correct_channel_id = await get_members_commands_channel_id(interaction.guild_id)
        if not correct_channel_id:
            await interaction.response.send_message("Questo server non è stato configurato!", ephemeral=True)
            return
        if interaction.channel_id != correct_channel_id:
            correct_channel = await interaction.guild.fetch_channel(correct_channel_id)
            await interaction.response.send_message(f"Devi scrivere i comandi in {correct_channel.mention}", ephemeral=True)
            return
        view = discord.ui.View()
        events = await get_events_for_guild(interaction.guild_id)
        event_selector = build_event_selector(events)
        if not event_selector:
            await interaction.response.send_message("Non ci sono eventi configurati per il tuo server!", ephemeral=True)
            return
        async def event_selector_callback(interaction: discord.Interaction):
            event_id = int(event_selector.values[0])
            players_per_team = await get_players_per_team(event_id)
            await interaction.response.send_modal(
                RegistraTeamModal(event_id=event_id, members_number=players_per_team)
            )
            
        event_selector.callback = event_selector_callback
        view.add_item(event_selector)
        embed = discord.Embed(
            title="Scegli l'evento a cui iscriverti",
            color=discord.Colour.red(),
            description="Questa è una lista degli eventi attivi.\nScegli l'evento a cui ti sei iscritto durante il ticket."
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Teams(bot))