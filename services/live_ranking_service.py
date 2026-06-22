import asyncio
import discord

from typing import Any

from services.event_service import get_event_info
from services.lobby_service import get_lobby
from services.ranking_service import compute_team_ranking, compute_mvp_ranking
from ui.embeds.event_builders import build_live_team_ranking_embed, build_live_mvp_ranking_embed


live_events: dict[int, dict[int, dict[int, Any]]] = {}


TIME_TO_WAIT: int = 35 * 60

async def live_mvp_loop(event_id: int, lobby_id: int):
    try:
        while True:
            await asyncio.sleep(TIME_TO_WAIT)

            event_state = live_events.get(event_id)
            if not event_state:
                return

            lobby_state = event_state.get(lobby_id)
            if not lobby_state:
                return

            event = lobby_state["event"]
            lobby = lobby_state["lobby"]

            try:
                ranking = await compute_mvp_ranking(
                    event_id,
                    scope="lobby",
                    lobby_id=lobby_id,
                    include_pending=True
                )
            except Exception as e:
                print(e)
                continue

            embed = build_live_mvp_ranking_embed(event.name, lobby.name, ranking)

            messages = lobby_state["mvp_messages"]

            for user_id, msg in list(messages.items()):
                try:
                    await msg.edit(embed=embed)
                except:
                    messages.pop(user_id, None)
    except asyncio.CancelledError:
        return

async def live_team_loop(event_id: int, lobby_id: int):
    try:
        while True:
            await asyncio.sleep(TIME_TO_WAIT)

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

            embed = build_live_team_ranking_embed(event.name, lobby.name, ranking)

            messages: dict[int, discord.Message] = lobby_state["messages"]

            for leader_id, msg in list(messages.items()):
                try:
                    await msg.edit(embed=embed)
                except:
                    messages.pop(leader_id, None)
    except asyncio.CancelledError:
        return

async def start_live(event_id: int, guild: discord.Guild, leader_ids: list[int], lobby_id: int):
    # 1. dati base
    event = await get_event_info(event_id, guild.id)
    if event is None:
        raise ValueError("Event is None")
    lobby = await get_lobby(event_id, lobby_id)

    if lobby is None or lobby.name is None or not lobby.teams:
        return
    state = live_events.get(event_id, {}).get(lobby_id)
    if state:
        team_task = state.get("team_task")
        mvp_task = state.get("mvp_task")

        if (team_task and not team_task.done()) or (mvp_task and not mvp_task.done()):
            return
    

    # 2. ranking iniziale
    ranking = await compute_team_ranking(
        event_id,
        scope="lobby",
        lobby_id=lobby_id,
        include_pending=True
    )

    embed = build_live_team_ranking_embed(event.name, lobby.name, ranking)

    # 3. invio DM ai leader
    team_messages: dict[int, discord.Message] = {}
    mvp_messages: dict[int, discord.Message] = {}

    for leader_id in leader_ids:
        member = guild.get_member(leader_id)
        if not member:
            continue

        try:
            msg = await member.send(embed=embed)
            team_messages[leader_id] = msg
        except:
            pass
    
    mvp_ranking = await compute_mvp_ranking(
        event_id,
        scope="lobby",
        lobby_id=lobby_id
    )

    mvp_embed = build_live_mvp_ranking_embed(event.name, lobby.name, mvp_ranking)

    for user_id in leader_ids:
        member = guild.get_member(user_id)
        if not member:
            continue

        try:
            msg = await member.send(embed=mvp_embed)
            mvp_messages[user_id] = msg
        except:
            pass
    

    # 4. crea task loop
    team_task = asyncio.create_task(live_team_loop(event_id, lobby_id))
    mvp_task = asyncio.create_task(live_mvp_loop(event_id, lobby_id))

    # 5. salva tutto nello stato
    live_events.setdefault(event_id, {})[lobby_id] = {
        "event": event,
        "lobby": lobby,
        "team_messages": team_messages,
        "mvp_messages": mvp_messages,
        "team_task": team_task,
        "mvp_task": mvp_task
    }

async def stop_live(event_id: int, lobby_id: int | None = None):
    if event_id not in live_events:
        return

    if lobby_id is None:
        for lid, data in live_events[event_id].items():
            if data.get("team_task"):
                data["team_task"].cancel()
            if data.get("mvp_task"):
                data["mvp_task"].cancel()

        live_events.pop(event_id, None)
        return

    lobby_state = live_events[event_id].pop(lobby_id, None)

    if lobby_state:
        if lobby_state.get("team_task"):
            lobby_state["team_task"].cancel()
        if lobby_state.get("mvp_task"):
            lobby_state["mvp_task"].cancel()

    if not live_events[event_id]:
        live_events.pop(event_id, None)