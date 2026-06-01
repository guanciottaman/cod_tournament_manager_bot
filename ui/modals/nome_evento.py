import discord

from services.event_service import *
from ui.embeds.event_builders import build_event_embed, DEFAULT_PLACEMENT_POINTS
from ui.views.crea_evento import CreaEventoView

class NomeEventoModal(discord.ui.Modal, title="Nuovo evento"):
    name = discord.ui.TextInput(label="Nome evento", placeholder="Inserisci il nome dell'evento...", max_length=40)
    async def on_submit(self, interaction: discord.Interaction):
        event_id = await create_event(interaction.guild_id, self.name.value)
        await set_players_per_team(event_id, 3)
        await set_kill_points_db(event_id, 1)
        await insert_placement_points(event_id, list(DEFAULT_PLACEMENT_POINTS.values()))
        event = await get_event_info(event_id, interaction.guild_id)
        placement_points = await get_placement_points(event_id)
        teams = await get_teams_by_event(event_id)
        embed = build_event_embed(event, placement_points, teams)
        
        await interaction.response.send_message(
            embed=embed,
            view=CreaEventoView(event_id),
            ephemeral=True
        )