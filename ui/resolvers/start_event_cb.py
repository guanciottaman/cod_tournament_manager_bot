import discord

from models.event import Event
from ui.embeds.lobby_builders import build_event_start_summary
from services.lobby_service import get_lobbies
from services.event_service import set_event_status

async def start_event_callback(interaction: discord.Interaction, event: Event):
    lobbies = await get_lobbies(event.event_id)
    embed = await build_event_start_summary(lobbies)
    embed.title = "Avvia evento"
    view = discord.ui.View()
    start_event_btn = discord.ui.Button(
        label="Avvia evento",
        style=discord.ButtonStyle.green
    )
    async def start_event_callback(interaction: discord.Interaction):
        await set_event_status(event.event_id, "running")
        await interaction.response.send_message("L'evento è stato avviato con successo!", ephemeral=True)
    start_event_btn.callback = start_event_callback
    view.add_item(start_event_btn)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

