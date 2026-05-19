import random

from models.lobby import Lobby
from models.team import Team
from services.team_service import get_teams
from db.db import *


MIN_PER_LOBBY = 2
MAX_PER_LOBBY = 15

async def create_lobbies(
    event_id: int,
    mode: str,
    lobbies_number: int | None = None
) -> list[Lobby]:

    teams = await get_teams(event_id)
    if not teams:
        return []

    if mode == "random":
        random.shuffle(teams)
    elif mode in ("kd", "kd_balanced"):
        teams.sort(key=lambda t: t.kd, reverse=True)
    else:
        raise ValueError("INVALID_MODE")


    if mode == "kd_balanced":
        if not lobbies_number:
            raise ValueError("lobbies_number required")

        lobbies: list[list[Team]] = [[] for _ in range(lobbies_number)]
        kd_sum = [0.0] * lobbies_number

        for t in teams:
            i = kd_sum.index(min(kd_sum))
            lobbies[i].append(t)
            kd_sum[i] += t.kd

    elif mode == "kd":
        lobbies = []
        current: list[Team] = []

        for t in teams:
            current.append(t)

            if len(current) == MAX_PER_LOBBY:
                lobbies.append(current)
                current = []

        if current:
            lobbies.append(current)

    else:
        if not lobbies_number:
            raise ValueError("lobbies_number required")

        lobbies = [[] for _ in range(lobbies_number)]

        for i, t in enumerate(teams):
            lobbies[i % lobbies_number].append(t)

    for l in lobbies:
        if len(l) > MAX_PER_LOBBY:
            return []
        if len(l) < MIN_PER_LOBBY:
            return []

    return [
        Lobby(i + 1, lobby)
        for i, lobby in enumerate(lobbies)
    ]


async def create_lobbies_db(event_id: int, names: list[str]):
    await execute("DELETE FROM lobbies WHERE event_id = ?", (event_id,))

    for name in names:
        await execute(
            "INSERT INTO lobbies (event_id, name) VALUES (?, ?)",
            (event_id, name)
        )


async def recreate_lobbies(event_id: int, lobbies: list[Lobby]):
    await execute("DELETE FROM lobbies WHERE event_id = ?", (event_id,))

    for i, lobby in enumerate(lobbies):
        name = f"Lobby {i+1}"

        await execute(
            "INSERT INTO lobbies (event_id, name) VALUES (?, ?)",
            (event_id, name)
        )

        row = await fetch_one(
            "SELECT lobby_id FROM lobbies WHERE event_id = ? AND name = ? ORDER BY lobby_id DESC LIMIT 1",
            (event_id, name)
        )

        lobby_id = row[0]
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
        SELECT lobby_id, name
        FROM lobbies
        WHERE event_id = ?
        ORDER BY lobby_id ASC
    """, (event_id,))

    return [
        Lobby(index=i + 1, name=row[1], teams=[])
        for i, row in enumerate(rows)
    ]