import discord

from typing import Any

from services.lobby_service import get_lobbies
from models.event import Event
from ui.resolvers.send_lobby_codes_cb import send_lobby_codes_callback

class SendLobbyCodeModal(discord.ui.Modal, title="Codice lobby"):
    codice_lobby: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="Codice lobby",
        placeholder="Inserisci il codice da mandare alla lobby",
    )
    def __init__(self, event: Event):
        super().__init__(title="Codice lobby")
        self.event = event

    async def on_submit(self, interaction: discord.Interaction):
        lobbies = await get_lobbies(self.event.event_id)
        await send_lobby_codes_callback(interaction, self.event, lobbies, self.codice_lobby.value)