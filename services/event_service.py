import datetime

from models.event import Event
from models.team import Team
from db.db import *


VALID_STATUSES = {"draft", "ready", "running", "finished"}

async def get_event_info(event_id: int, guild_id: int) -> Event | None:
    row_events = await fetch_one("""
        SELECT name, status, created_at
        FROM events
        WHERE event_id = ? AND guild_id = ?
    """, (event_id, guild_id))


    if row_events is None:
        return None

    row_settings = await fetch_one("""
        SELECT kill_points, players_per_team, drop_worst_match,
               matches_number, kd_mode, lobbies_number
        FROM events_settings
        WHERE event_id = ?
    """, (event_id,))

    if row_settings is None:
        return None

    event = Event(
        event_id=event_id,
        guild_id=guild_id,
        name=row_events[0],
        status=row_events[1],
        created_at=datetime.datetime.fromisoformat(row_events[2]),

        kill_points=row_settings[0],
        players_per_team=row_settings[1],
        drop_worst_match=bool(row_settings[2]),
        matches_number=row_settings[3],
        kd_mode=bool(row_settings[4]),
        lobbies_number=row_settings[5]
    )
    return event

async def get_event_settings(event_id: int):
    row = await fetch_one("""
        SELECT kd_mode, lobbies_number
        FROM events_settings
        WHERE event_id = ?
    """, (event_id,))
    return row

async def get_placement_points(event_id: int) -> list[tuple[int, int]]:
    rows = await fetch_all("""
        SELECT position, points
        FROM placement_points
        WHERE event_id = ?
        ORDER BY position ASC
    """, (event_id,))
    return rows or []



async def get_events_for_guild(guild_id: int, statuses: list[str] | None = None):
    query = "SELECT event_id, name FROM events WHERE guild_id = ?"
    params = [guild_id]

    if statuses:
        placeholders = ",".join(["?"] * len(statuses))
        query += f" AND status IN ({placeholders})"
        params.extend(statuses)

    return await fetch_all(query, tuple(params))

async def insert_placement_points(event_id: int, values: list[str]):
    await execute("DELETE FROM placement_points WHERE event_id = ?", (event_id,))
    for i, val in enumerate(values):
        await execute("""
            INSERT INTO placement_points (event_id, position, points) VALUES (?, ?, ?)
        """, (event_id, i+1, val))

async def set_matches_number(event_id: int, value: int):
    await execute(
        "UPDATE events_settings SET matches_number = ? WHERE event_id = ?",
        (value, event_id)
    )


async def get_matches_number(event_id: int):
    matches_number = await fetch_one(
        "SELECT matches_number FROM events_settings WHERE event_id = ?",
        (event_id,)
    )
    return matches_number[0] if matches_number else None


async def set_players_per_team(event_id: int, value: int):
    await execute("""
        UPDATE events_settings SET players_per_team = ? WHERE event_id = ?
    """, (value, event_id))

async def get_players_per_team(event_id: int):
    row = await fetch_one(
        "SELECT players_per_team FROM events_settings WHERE event_id = ?",
        (event_id,)
    )
    return row[0] if row else None


async def set_kd_mode(event_id: int, value: int):
    await execute("""
        UPDATE events_settings
        SET kd_mode = ?
        WHERE event_id = ?
    """, (value, event_id))

async def set_drop_worst_match(event_id: int, value: int):
    await execute("""
        UPDATE events_settings
        SET drop_worst_match = ?
        WHERE event_id = ?
    """, (value, event_id))

async def set_event_status(event_id: int, status: str):
    await execute(
        "UPDATE events SET status = ? WHERE event_id = ?",
        (status, event_id)
    )

async def set_lobbies_number(event_id: int, value: int):
    await execute(
        "UPDATE events_settings SET lobbies_number = ? WHERE event_id = ?",
        (value, event_id)
    )

async def create_event(guild_id: int, name: str) -> int:
    await execute(
        "INSERT INTO events (guild_id, name, status, created_at) VALUES (?, ?, ?, datetime('now'))",
        (guild_id, name, "draft")
    )

    row = await fetch_one(
        "SELECT event_id FROM events WHERE guild_id = ? AND name = ? ORDER BY event_id DESC LIMIT 1",
        (guild_id, name)
    )

    event_id = row[0]

    await execute(
        "INSERT INTO events_settings (event_id) VALUES (?)",
        (event_id,)
    )

    return event_id

async def delete_event(guild_id: int, event_id: int):
    await execute("DELETE FROM events WHERE guild_id = ? AND event_id = ?", (guild_id, event_id))

async def get_teams_by_event(event_id: int):
    rows = await fetch_all(
        "SELECT team_id, name, leader_discord_id FROM teams WHERE event_id = ?",
        (event_id,)
    )

    return [
        Team(
            team_id=row[0],
            name=row[1],
            leader_discord_id=row[2]
        )
        for row in rows
    ]

async def get_team_info(team_id: int):
    row = await fetch_one("SELECT name, leader_discord_id FROM teams WHERE team_id = ?", (team_id,))
    if not row:
        return None
    return Team(
        team_id=team_id,
        name=row[0],
        leader_discord_id=row[1]
    )

async def get_team_members(team_id: int):
    team_members = await fetch_all(
        "SELECT member_name FROM team_members WHERE team_id = ?",
        (team_id,)
    )
    return team_members


async def delete_team(team_id: int):
    await execute("DELETE FROM teams WHERE team_id = ?", (team_id,))
