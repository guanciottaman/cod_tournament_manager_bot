import random

from models.lobby import Lobby
from models.team import Team
from services.team_service import get_teams
from services.event_service import get_event_info
from db.db import *


MIN_PER_LOBBY = 2
MAX_PER_LOBBY = 15


def generate_lobbies(
    teams: list[Team],
    mode: str,
    lobbies_number: int | None = None
) -> list[list[Team]]:

    if not teams:
        return []

    teams = teams[:]  # SEMPRE safe copy

    if mode == "random":
        random.shuffle(teams)

    elif mode in ("kd", "kd_balanced"):
        teams.sort(key=lambda t: t.kd or 0)

    else:
        raise ValueError("INVALID_MODE")

    # KD BALANCED
    if mode == "kd_balanced":
        if not lobbies_number:
            raise ValueError("lobbies_number required")
        lobbies: list[list[Team]] = [[] for _ in range(lobbies_number)]
        direction = 1
        i = 0

        for t in teams:
            lobbies[i].append(t)

            i += direction

            if i == lobbies_number:
                i = lobbies_number - 1
                direction = -1
            elif i < 0:
                i = 0
                direction = 1
        return lobbies
    # KD SEQUENTIAL
    elif mode == "kd":
        if not lobbies_number:
            raise ValueError("lobbies_number required")

        lobbies = []
        current = []

        for t in teams:
            current.append(t)

            if len(current) == MAX_PER_LOBBY:
                lobbies.append(current)
                current = []

        if current:
            lobbies.append(current)

    # RANDOM / DEFAULT
    else:
        if not lobbies_number:
            raise ValueError("lobbies_number required")

        lobbies = [[] for _ in range(lobbies_number)]

        for i, t in enumerate(teams):
            lobbies[i % lobbies_number].append(t)

    # FIX IMPORTANTE: evita lobbies vuote "false positive"
    if any(not l for l in lobbies):
        raise ValueError("EMPTY_LOBBY_ERROR")

    return lobbies

async def create_lobbies_db(event_id: int, names: list[str]) -> list[int]:
    await execute("DELETE FROM lobbies WHERE event_id = ?", (event_id,))

    lobby_ids: list[int] = []

    for name in names:
        lobby_id = await execute(
            "INSERT INTO lobbies (event_id, name) VALUES (?, ?)",
            (event_id, name)
        )
        lobby_ids.append(lobby_id)

    return lobby_ids

async def update_lobbies_db(event_id: int, lobby_ids: list[int], names: list[str]):
    for lobby_id, name in zip(lobby_ids, names):
        await execute(
            "UPDATE lobbies SET name = ? WHERE lobby_id = ?",
            (name, lobby_id)
        )

async def delete_lobbies(event_id: int):
    await execute("DELETE FROM lobbies WHERE event_id = ?", (event_id,))

async def rebuild_lobbies(event_id: int, lobbies_number: int):
    names = await get_lobbies_names(event_id)

    if not names or len(names) != lobbies_number:
        defaults = ["Easy", "Medium", "Hard"]

        names = [
            (defaults[i] if i < 3 else f"Lobby {i+1}")
            for i in range(lobbies_number)
        ]

    await delete_lobbies(event_id)

    lobby_ids = await create_lobbies_db(event_id, names)

    return lobby_ids, names

async def apply_lobbies(lobby_ids: list[int], lobbies_structure: list[list[Team]]):
    queries: list[tuple[int, int]] = []

    for lobby_id, teams in zip(lobby_ids, lobbies_structure):
        for team in teams:
            queries.append((lobby_id, team.team_id))

    for lobby_id, team_id in queries:
        await execute(
            "UPDATE teams SET lobby_id = ? WHERE team_id = ?",
            (lobby_id, team_id)
        )


async def recreate_lobbies(event_id: int, lobbies: list[Lobby]):
    existing = await fetch_all("""
        SELECT lobby_id, name
        FROM lobbies
        WHERE event_id = ?
        ORDER BY lobby_id ASC
    """, (event_id,))

    if len(existing) != len(lobbies):
        raise ValueError("Lobby config mismatch")

    for (lobby_id, name), lobby in zip(existing, lobbies):
        lobby.lobby_id = lobby_id
        lobby.name = name

        for team in lobby.teams:
            await execute(
                "UPDATE teams SET lobby_id = ? WHERE team_id = ?",
                (lobby_id, team.team_id)
            )


async def get_lobbies_names(event_id: int):
    rows = await fetch_all(
        "SELECT name FROM lobbies WHERE event_id = ?",
        (event_id,)
    )
    return [row[0] for row in rows]

async def get_lobbies(event_id: int) -> list[Lobby]:
    rows = await fetch_all("""
        SELECT 
            l.lobby_id,
            l.name,
            t.team_id,
            t.name,
            t.leader_discord_id,
            t.kd
        FROM lobbies l
        LEFT JOIN teams t ON t.lobby_id = l.lobby_id
        WHERE l.event_id = ?
        ORDER BY l.lobby_id ASC, t.kd DESC
    """, (event_id,))

    lobbies_map: dict[int, Lobby] = {}

    for lobby_id, lobby_name, team_id, team_name, team_leader_discord_id, team_kd in rows:

        if lobby_id not in lobbies_map:
            lobbies_map[lobby_id] = Lobby(
                index=len(lobbies_map)+1,
                name=lobby_name,
                teams=[]
            )

        if team_id is not None:
            lobbies_map[lobby_id].teams.append(
                Team(team_id, team_name, team_leader_discord_id, team_kd)
            )

    return list(lobbies_map.values())


async def set_lobbies_number(event_id: int, new_number: int):
    await execute("UPDATE events_settings SET lobbies_number = ? WHERE event_id = ?",
        (new_number, event_id))

async def update_lobbies_config(event_id: int, guild_id: int, new_number: int, mode: str):
    event = await get_event_info(event_id, guild_id)

    if event.status != "ready":
        raise ValueError("Cannot modify running event")

    names = await get_lobbies_names(event_id)
    defaults = ["Easy", "Medium", "Hard"]

    if not names:
        if mode in ("kd", "kd_balanced"):
            names = defaults[:new_number]
        else:
            names = [f"Lobby {i+1}" for i in range(new_number)]
    else:
        names = names[:new_number] + [
            f"Lobby {i+1}" for i in range(len(names), new_number)
        ]

    await execute("DELETE FROM lobbies WHERE event_id = ?", (event_id,))
    await create_lobbies_db(event_id, names)