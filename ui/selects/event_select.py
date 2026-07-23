import discord

from typing import Any

from models.event import Event

def build_event_selector(events: list[Event]) -> discord.ui.Select[Any] | None:
    if not events:
        return None

    return discord.ui.Select(
        placeholder="Seleziona l'evento...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=event.name, value=str(event.event_id))
            for event in events
        ]
    )