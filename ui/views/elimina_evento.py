import discord

from typing import Any

from services.event_service import delete_event, delete_lobbies_roles, delete_teams_category, delete_lobbies_category
from services.live_ranking_service import stop_live

class EliminaEventoView(discord.ui.View):
    def __init__(self, event_id: int):
        super().__init__(timeout=None)
        self.event_id = event_id
    
    @discord.ui.button(
        label="Annulla",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_delete_event(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        await interaction.response.send_message("Eliminazione evento annullata.", ephemeral=True)

    @discord.ui.button(
            label="🗑️Conferma eliminazione",
            style=discord.ButtonStyle.danger
    )
    async def delete_event_confirm(self, interaction: discord.Interaction, button: discord.ui.Button[Any]):
        if interaction.guild is None:
            return
        await stop_live(self.event_id)
        await delete_teams_category(self.event_id, interaction.guild)
        await delete_lobbies_category(event_id, interaction.guild)
        await delete_lobbies_roles(self.event_id, interaction.guild)
        await delete_event(interaction.guild.id, self.event_id)
        await interaction.response.send_message("Evento eliminato con successo!", ephemeral=True)