import discord
import asyncio

from models.event import Event
from ui.embeds.lobby_builders import build_event_start_summary
from services.lobby_service import get_lobbies
from services.event_service import set_event_status, get_leader_ids
from services.live_ranking_service import start_live
from services.server_service import get_admin_role_id

async def start_event_callback(interaction: discord.Interaction, event: Event):
    lobbies = await get_lobbies(event.event_id)
    embed = await build_event_start_summary(lobbies)
    embed.title = "Avvia evento"
    view = discord.ui.View()
    start_event_btn = discord.ui.Button(
        label="Avvia evento",
        style=discord.ButtonStyle.green
    )
    async def confirm_start(interaction: discord.Interaction):
        await set_event_status(event.event_id, "running")
        await interaction.response.send_message(
            "L'evento è stato avviato con successo!",
            ephemeral=True
        )
        for lobby in lobbies:
            try:
                asyncio.create_task(
                    start_live(event.event_id, interaction.guild, lobby.lobby_id)
                )
            except Exception as e:
                print(f"start_live error lobby {lobby.lobby_id}: {e}")
    start_event_btn.callback = confirm_start
    view.add_item(start_event_btn)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

