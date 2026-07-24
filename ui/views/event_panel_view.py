import discord

from typing import Any

from models.event import Event
from services.event_service import get_event_info, get_placement_points, get_teams_by_event, get_events_for_guild
from services.server_service import get_ranking_channel_id
from ui.embeds.event_builders import build_event_embed
from services.event_flow import resolve_event
from ui.views.elimina_evento import EliminaEventoView
from ui.resolvers.termina_evento_cb import termina_evento_callback


class EliminaButton(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Elimina evento",
            emoji="🗑️",
            style=discord.ButtonStyle.red,
            row=0,
            custom_id=f"event_panel:elimina:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
            return
        embed = discord.Embed(
            title="Elimina evento",
            color=discord.Color.red(),
            description=f"Stai per eliminare l'evento **{event.name}**. Sei sicuro?"
        )
        await interaction.response.send_message(
            embed=embed,
            view=EliminaEventoView(self.event_id),
            ephemeral=True
        )

class TerminaButton(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Termina evento",
            emoji="🛑",
            style=discord.ButtonStyle.red,
            row=0,
            custom_id=f"event_panel:termina:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        embed = discord.Embed(
            title="Termina evento",
            color=discord.Color.red(),
            description="Questa è una lista degli eventi in corso. Scegli quale vuoi terminare."
        )
        events = await get_events_for_guild(interaction.guild.id, ["running"])
        async def wrapper(interaction: discord.Interaction, event: Event):
            if interaction.guild is None:
                return
            ranking_channel_id = await get_ranking_channel_id(interaction.guild.id)
            if ranking_channel_id is None:
                await interaction.response.send_message("Server non configurato correttamente!", ephemeral=True)
                return
            ranking_channel = interaction.guild.get_channel(ranking_channel_id)
            if not isinstance(ranking_channel, discord.TextChannel):
                await interaction.response.send_message("Canale classifiche non trovato!", ephemeral=True)
                return
            await termina_evento_callback(interaction, event, ranking_channel, True)
        await resolve_event(interaction, embed, events, wrapper)

class RicaricaButton(discord.ui.Button[Any]):
    def __init__(self, event_id: int):
        super().__init__(
            label="Ricarica",
            emoji="🔄",
            style=discord.ButtonStyle.grey,
            row=1,
            custom_id=f"event_panel:ricarica:{event_id}"
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        event = await get_event_info(self.event_id, interaction.guild.id)
        if event is None:
            await interaction.response.send_message("Evento non trovato!", ephemeral=True)
            return
        placement_points = await get_placement_points(self.event_id)
        teams = await get_teams_by_event(self.event_id)
        await interaction.response.edit_message(
            embed=build_event_embed(
                event, interaction.guild, placement_points, teams
            )
        )

class EventPanelView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)

        self.add_item(TerminaButton(event_id))
        self.add_item(RicaricaButton(event_id))