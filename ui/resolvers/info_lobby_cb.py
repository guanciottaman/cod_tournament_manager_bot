import discord

from models.event import Event
from services.lobby_service import get_lobbies
from services.team_service import get_inserted_matches_count
from ui.embeds.lobby_builders import build_info_lobby_embed

async def info_lobbies_callback(interaction: discord.Interaction, event: Event):
    lobbies = await get_lobbies(event.event_id)
    if event.status == "running":
        inserted_matches_count = await get_inserted_matches_count(event.event_id)
        matches_number = event.matches_number
        embed = build_info_lobby_embed(
            event.name,
            lobbies,
            show_matches=True,
            inserted_matches_count=inserted_matches_count,
            matches_number=matches_number
        )
    else:
        embed = build_info_lobby_embed(event.name, lobbies)
    await interaction.response.send_message(embed=embed, ephemeral=True)