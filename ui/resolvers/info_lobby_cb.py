import discord

from models.event import Event
from services.lobby_service import get_lobbies
from ui.embeds.lobby_builders import build_info_lobby_embed

async def info_lobbies_callback(interaction: discord.Interaction, event: Event):
    lobbies = await get_lobbies(event.event_id)
    embed = build_info_lobby_embed(event.name, lobbies)
    await interaction.response.send_message(embed=embed, ephemeral=True)