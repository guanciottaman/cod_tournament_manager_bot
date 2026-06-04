import discord

from typing import Callable, Awaitable

from models.event import Event
from ui.selects.event_select import build_event_selector
from services.event_service import get_event_info

EventCallback = Callable[[discord.Interaction, Event], Awaitable[None]]

async def resolve_event(
    interaction: discord.Interaction,
    embed: discord.Embed,
    events: list[Event],
    callback: EventCallback
):
    if not events:
        await interaction.response.send_message(
            "Non ci sono eventi disponibili.",
            ephemeral=True
        )
        return

    if len(events) == 1:
        await callback(interaction, events[0])
        return

    view = discord.ui.View()
    selector = build_event_selector(events)
    if selector is None:
        await interaction.response.send_message("C'è stato un errore!", ephemeral=True)
        return

    async def _cb(interaction: discord.Interaction):
        event_id = int(selector.values[0])
        event = await get_event_info(event_id, interaction.guild_id)

        if event is None:
            await interaction.response.send_message("Evento non valido", ephemeral=True)
            return

        await callback(interaction, event)

    selector.callback = _cb
    view.add_item(selector)

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )