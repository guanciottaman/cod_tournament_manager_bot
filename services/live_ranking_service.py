import asyncio
import discord

from typing import Any

from services.event_service import get_event_info, get_matches_number, get_drop_worst_match
from services.server_service import get_live_ranking_channel_id
from services.team_service import get_inserted_matches_count
from services.lobby_service import get_lobby
from services.ranking_service import compute_team_ranking, compute_mvp_ranking
from ui.embeds.event_builders import build_live_team_ranking_embed, build_live_mvp_ranking_embed


live_events: dict[int, dict[int, dict[str, Any]]] = {}


TIME_TO_WAIT: int = 5

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
            drop_worst_match = await get_drop_worst_match(event_id)
            embed = build_live_mvp_ranking_embed(
                event.name,
                lobby.name,
                ranking,
                drop_worst_match
            )

            msg = lobby_state["mvp_message"]
            try:
                await msg.edit(embed=embed)
            except discord.NotFound:
                live_events.get(event_id, {}).pop(lobby_id, None)
                return
            except discord.HTTPException:
                pass
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
            inserted_matches = await get_inserted_matches_count(event_id)
            matches_number = await get_matches_number(event_id)
            if matches_number is None:
                raise ValueError("Matches number not found")
            drop_worst_match = await get_drop_worst_match(event_id)

            embed = build_live_team_ranking_embed(
                event.name,
                lobby.name,
                ranking,
                inserted_matches,
                matches_number,
                drop_worst_match
            )

            msg = lobby_state["team_message"]

            try:
                await msg.edit(embed=embed)
            except discord.NotFound:
                return
            except discord.HTTPException:
                pass
    except asyncio.CancelledError:
        return

async def start_live(event_id: int, guild: discord.Guild, lobby_id: int):
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
    inserted_matches = await get_inserted_matches_count(event_id)
    matches_number = await get_matches_number(event_id)
    if matches_number is None:
        raise ValueError("Matches number not found")
    
    # 3. invio DM al canale
    live_ranking_channel_id = await get_live_ranking_channel_id(guild.id)
    if live_ranking_channel_id is None:
        raise ValueError("Missing live channel")
    try:
        live_ranking_channel = guild.get_channel(live_ranking_channel_id)
        if live_ranking_channel is None:
            live_ranking_channel = await guild.fetch_channel(live_ranking_channel_id)
    except discord.NotFound:
        raise ValueError("Live channel deleted")
    except discord.Forbidden:
        raise ValueError("No permission to access live channel")
    except discord.HTTPException:
        raise ValueError("Missing live channel")
    drop_worst_match = await get_drop_worst_match(event_id)
    team_embed = build_live_team_ranking_embed(
        event.name,
        lobby.name,
        ranking,
        inserted_matches,
        matches_number,
        drop_worst_match
    )

    team_msg = await live_ranking_channel.send(embed=team_embed)
    
    mvp_ranking = await compute_mvp_ranking(
        event_id,
        scope="lobby",
        lobby_id=lobby_id
    )

    mvp_embed = build_live_mvp_ranking_embed(
        event.name,
        lobby.name,
        mvp_ranking,
        drop_worst_match
    )

    mvp_msg = await live_ranking_channel.send(embed=mvp_embed)
    

    live_events.setdefault(event_id, {})[lobby_id] = {
        "event": event,
        "lobby": lobby,
        "team_message": team_msg,
        "mvp_message": mvp_msg,
        "team_task": None,
        "mvp_task": None
    }

    team_task = asyncio.create_task(live_team_loop(event_id, lobby_id))
    mvp_task = asyncio.create_task(live_mvp_loop(event_id, lobby_id))

    live_events[event_id][lobby_id]["team_task"] = team_task
    live_events[event_id][lobby_id]["mvp_task"] = mvp_task

async def stop_live(event_id: int, lobby_id: int | None = None):
    if event_id not in live_events:
        return

    async def cancel_task(task: asyncio.Task | None):
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # stop all lobbies of event
    if lobby_id is None:
        for lid, data in list(live_events[event_id].items()):
            await cancel_task(data.get("team_task"))
            await cancel_task(data.get("mvp_task"))

        live_events.pop(event_id, None)
        return

    # stop single lobby
    lobby_state = live_events[event_id].pop(lobby_id, None)

    if lobby_state:
        await cancel_task(lobby_state.get("team_task"))
        await cancel_task(lobby_state.get("mvp_task"))

    # cleanup event if empty
    if not live_events.get(event_id):
        live_events.pop(event_id, None)