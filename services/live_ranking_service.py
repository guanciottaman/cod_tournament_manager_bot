import asyncio
import discord

from typing import Any

from services.event_service import get_event_info
from services.lobby_service import get_lobby
from services.ranking_service import compute_team_ranking
from ui.embeds.event_builders import build_live_ranking_embed


live_events: dict[int, dict[int, dict[int, Any]]] = {}


async def live_loop(event_id: int, lobby_id: int):
    while True:
        await asyncio.sleep(35 * 60)

        event_state = live_events.get(event_id)
        if not event_state:
            return

        lobby_state = event_state.get(lobby_id)
        if not lobby_state:
            return

        event = lobby_state["event"]
        lobby = lobby_state["lobby"]

        try:
            ranking = await compute_team_ranking(
                event_id,
                scope="lobby",
                lobby_id=lobby_id,
                include_pending=True
            )
        except Exception as e:
            print(e)
            continue

        embed = build_live_ranking_embed(event.name, lobby.name, ranking)

        messages: dict[int, discord.Message] = lobby_state["messages"]

        for leader_id, msg in list(messages.items()):
            try:
                await msg.edit(embed=embed)
            except:
                messages.pop(leader_id, None)

async def start_live(event_id: int, guild: discord.Guild, leader_ids: list[int], lobby_id: int):
    # 1. dati base
    event = await get_event_info(event_id, guild.id)
    if event is None:
        raise ValueError("Event is None")
    if event.event_id in live_events and lobby_id in live_events[event_id]:
        return
    lobby = await get_lobby(event_id, lobby_id)

    if lobby is None or lobby.name is None or not lobby.teams:
        return

    # 2. ranking iniziale
    ranking = await compute_team_ranking(
        event_id,
        scope="lobby",
        lobby_id=lobby_id,
        include_pending=True
    )

    embed = build_live_ranking_embed(event.name, lobby.name, ranking)

    # 3. invio DM ai leader
    messages: dict[int, discord.Message] = {}

    for leader_id in leader_ids:
        member = guild.get_member(leader_id)
        if not member:
            continue

        try:
            msg = await member.send(embed=embed)
            messages[leader_id] = msg
        except:
            pass
    

    # 4. crea task loop
    task = asyncio.create_task(live_loop(event_id, lobby_id))

    # 5. salva tutto nello stato
    live_events.setdefault(event_id, {})[lobby_id] = {
        "event": event,
        "lobby": lobby,
        "messages": messages,
        "task": task
    }


async def stop_live(event_id: int, lobby_id: int | None = None):
    if event_id not in live_events:
        return

    # stop tutto evento
    if lobby_id is None:
        for lid, data in live_events[event_id].items():
            task = data.get("task")
            if task:
                task.cancel()

        live_events.pop(event_id, None)
        return

    # stop singola lobby
    lobby_state = live_events[event_id].pop(lobby_id, None)

    if lobby_state:
        task = lobby_state.get("task")
        if task:
            task.cancel()

    if not live_events[event_id]:
        live_events.pop(event_id, None)