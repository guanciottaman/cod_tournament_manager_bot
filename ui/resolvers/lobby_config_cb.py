import discord

import math

from models.event import Event
from services.event_service import get_teams_by_event
from services.lobby_service import create_lobbies_db
from ui.views.lobbies_views import LobbyConfigView
from ui.embeds.lobby_builders import build_config_lobbies_embed


async def start_lobby_config(interaction: discord.Interaction, event: Event):
    teams = await get_teams_by_event(event.event_id)
    teams_count = len(teams)
    if teams_count < 2:
        await interaction.response.send_message("Non ci sono abbastanza team per iniziare un evento!", ephemeral=True)
        return

    lobby_mode = event.lobby_mode
    lobbies_number = min(5, max(1, math.ceil(teams_count / 16)))
    print(lobbies_number)
    lobby_ids: list[int] = await create_lobbies_db(event.event_id, [f"{i+1}" for i in range(lobbies_number)])
    embed = await build_config_lobbies_embed(
        event.event_id,
        lobbies_number,
        teams_count
    )
    await interaction.response.send_message(
        embed=embed,
        view=LobbyConfigView(event.event_id, teams_count, lobby_mode, lobby_ids, lobbies_number),
        ephemeral=True
    )