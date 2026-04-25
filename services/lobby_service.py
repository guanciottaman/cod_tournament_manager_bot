import random

from models.lobby import Lobby
from services.team_service import get_teams
from db.db import *


async def create_lobbies(event_id: int, kd_mode: bool, lobbies_number: int) -> list[Lobby]:
    teams = await get_teams(event_id)
    if not teams:
        return None
    
    if lobbies_number * 2 > len(teams):
        return None 

    if kd_mode:
        teams.sort(key=lambda t: t.kd, reverse=True)
    else:
        random.shuffle(teams)

    chunk_size = len(teams) // lobbies_number
    remainder = len(teams) % lobbies_number

    lobbies = []
    start = 0

    for i in range(lobbies_number):
        extra = 1 if i < remainder else 0
        end = start + chunk_size + extra

        lobby_teams = teams[start:end]
        lobbies.append(Lobby(i+1, lobby_teams))

        start = end

    return lobbies


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