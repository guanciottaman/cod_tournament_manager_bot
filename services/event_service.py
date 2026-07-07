import discord

import datetime

from models.event import Event
from models.team import Team
from db.db import *

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
            matches_number, lobby_mode, lobbies_number
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
        lobby_mode=row_settings[4],
        lobbies_number=row_settings[5]
    )
    return event

async def get_event_settings(event_id: int):
    row = await fetch_one("""
        SELECT lobby_mode, lobbies_number
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

async def get_drop_worst_match(event_id: int) -> bool:
    row = await fetch_one(
        "SELECT drop_worst_match FROM events_settings WHERE event_id = ?",
        (event_id,)
    )
    return bool(row[0]) if row else False

async def get_events_for_guild(
    guild_id: int,
    statuses: list[str] | None = None
) -> list[Event]:

    query = """
        SELECT
            e.event_id,
            e.guild_id,
            e.name,
            e.created_at,
            e.status,

            s.kill_points,
            s.players_per_team,
            s.drop_worst_match,
            s.matches_number,
            s.lobby_mode,
            s.lobbies_number

        FROM events e
        LEFT JOIN events_settings s ON s.event_id = e.event_id
        WHERE e.guild_id = ?
    """
    params: list = [guild_id]

    if statuses:
        placeholders = ",".join("?" for _ in statuses)
        query += f" AND e.status IN ({placeholders})"
        params.extend(statuses)

    query += " ORDER BY e.event_id DESC"
    rows = await fetch_all(query, tuple(params))
    return [
        Event(
            event_id=row[0],
            guild_id=row[1],
            name=row[2],
            created_at=row[3],
            status=row[4],
            kill_points=row[5],
            players_per_team=row[6],
            drop_worst_match=row[7],
            matches_number=row[8],
            lobby_mode=row[9],
            lobbies_number=row[10]
        )
        for row in rows
    ]

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


async def set_lobby_mode(event_id: int, value: str):
    await execute("""
        UPDATE events_settings
        SET lobby_mode = ?
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
    if not row:
        return None

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
        "SELECT team_id, name, leader_discord_id, kd, lobby_id FROM teams WHERE event_id = ?",
        (event_id,)
    )

    return [
        Team(
            team_id=row[0],
            name=row[1],
            leader_discord_id=row[2],
            kd=row[3],
            lobby=row[4]
        )
        for row in rows
    ]

async def get_team_info(team_id: int):
    row = await fetch_one("SELECT name, leader_discord_id, kd, lobby_id FROM teams WHERE team_id = ?", (team_id,))
    if not row:
        return None
    return Team(
        team_id=team_id,
        name=row[0],
        leader_discord_id=row[1],
        kd=row[2],
        lobby=row[3]
    )

async def get_team_members(team_id: int):
    team_members = await fetch_all(
        "SELECT member_name FROM team_members WHERE team_id = ?",
        (team_id,)
    )
    return team_members


async def delete_team(team_id: int, status: str):
    if status == "setup":
        await execute("""
            UPDATE teams
            SET previous_lobby_id = lobby_id,
                lobby_id = NULL,
                leader_discord_id = NULL
            WHERE team_id = ?
        """, (team_id,))
    else:
        await execute("DELETE FROM teams WHERE team_id = ?", (team_id,))


async def set_kill_points_db(event_id: int, kill_points: int):
    await execute(
        "UPDATE events_settings SET kill_points = ? WHERE event_id = ?",
        (kill_points, event_id)
    )

async def get_leader_ids(event_id: int, lobby_id: int | None = None):
    query = "SELECT leader_discord_id FROM teams WHERE event_id = ?"
    params = [event_id]
    if lobby_id is not None:
        query += " AND lobby_id = ?"
        params.append(lobby_id)
    rows = await fetch_all(query, tuple(params))
    return [r[0] for r in rows if r[0] is not None]

async def get_team_from_leader(event_id: int, leader_id: int):
    row = await fetch_one(
        "SELECT team_id, name, lobby_id, leader_discord_id, kd FROM teams WHERE event_id = ? AND leader_discord_id = ?",
        (event_id, leader_id)
    )
    if row is None:
        return None
    return Team(
        row[0],
        row[1],
        row[3],
        row[4],
        row[2]
    )

async def has_free_slot(event_id: int) -> bool:
    row = await fetch_one("""
        SELECT 1
        FROM teams
        WHERE event_id = ?
        AND lobby_id IS NULL
        LIMIT 1
    """, (event_id,))

    return row is not None

async def add_event_host_db(event_id: int, member_id: int):
    await execute("""
        INSERT OR IGNORE INTO event_hosts (event_id, member_id)
        VALUES (?, ?)
    """, (event_id, member_id))

async def remove_event_host_db(event_id: int, member_id: int):
    await execute("""
        DELETE FROM event_hosts
        WHERE event_id = ? AND member_id = ?
    """, (event_id, member_id))

async def get_event_hosts_db(event_id: int) -> list[int]:
    rows = await fetch_all("""
        SELECT member_id
        FROM event_hosts
        WHERE event_id = ?
    """, (event_id,))

    return [r[0] for r in rows]

async def is_event_host(event_id: int, member_id: int) -> bool:
    row = await fetch_one("""
        SELECT 1
        FROM event_hosts
        WHERE event_id = ? AND member_id = ?
    """, (event_id, member_id))

    return row is not None

async def get_duplicate_team_score(team_score_id: int) -> int | None:
    row = await fetch_one("""
        SELECT ts2.id
        FROM team_scores ts
        JOIN teams t ON t.team_id = ts.team_id
        JOIN team_scores ts2
            ON ts2.event_id = ts.event_id
            AND ts2.match_number = ts.match_number
            AND ts2.placement = ts.placement
            AND ts2.id != ts.id
        JOIN teams t2
            ON t2.team_id = ts2.team_id
            AND t2.lobby_id = t.lobby_id
        WHERE ts.id = ?
        LIMIT 1
    """, (team_score_id,))

    return row[0] if row else None

async def get_lobby_codes_channel(event_id: int, lobby_id: int) -> int | None:
    row = await fetch_one(
        "SELECT channel_id FROM lobby_codes_channels WHERE event_id = ? AND lobby_id = ?",
        (event_id, lobby_id)
    )
    if row is None:
        return None
    else:
        return row[0]

async def get_lobby_codes_channels(event_id: int) -> dict[int, int] | None:
    rows = await fetch_all(
        "SELECT channel_id, lobby_id FROM lobby_codes_channels WHERE event_id = ?",
        (event_id,)
    )
    if not rows:
        return None
    else:
        return {row[1]: row[0] for row in rows}

async def set_lobby_codes_channels(event_id: int, lobby_channels: dict[int, int]):
    for lobby_id, channel_id in lobby_channels.items():
        try:
            await execute(
                "INSERT INTO lobby_codes_channels (channel_id, event_id, lobby_id) VALUES (?, ?, ?)",
                (channel_id, event_id, lobby_id)
            )
        except aiosqlite.IntegrityError:
            raise ValueError("Lobby channel already exists")

async def create_lobbies_roles(event_id: int, guild: discord.Guild):
    rows = await fetch_all(
        "SELECT lobby_id, name FROM lobbies WHERE event_id = ?",
        (event_id,)
    )

    created_roles: list[discord.Role] = []

    try:
        for lobby_id, name in rows:
            role = await guild.create_role(
                name=f"LOBBY {name}",
                reason=f"Ruolo creato per l'evento {event_id}"
            )

            created_roles.append(role)

            await execute(
                """
                INSERT INTO lobbies_roles 
                (role_id, event_id, lobby_id)
                VALUES (?, ?, ?)
                """,
                (role.id, event_id, lobby_id)
            )

    except Exception:
        for role in created_roles:
            await role.delete(reason="Rollback creazione lobby roles")
        raise

async def get_lobby_role(event_id: int, lobby_id: int) -> int | None:
    row = await fetch_one(
        "SELECT role_id FROM lobbies_roles WHERE event_id = ? AND lobby_id = ?",
        (event_id, lobby_id)
    )
    return row[0] if row else None

async def get_lobby_roles(event_id: int) -> list[int] | None:
    rows = await fetch_all(
        "SELECT role_id FROM lobbies_roles WHERE event_id = ?",
        (event_id,)
    )
    if not rows:
        return None
    return [r[0] for r in rows]

async def delete_lobbies_roles(event_id: int, guild: discord.Guild):
    rows = await fetch_all(
        "SELECT role_id FROM lobbies_roles WHERE event_id = ?",
        (event_id,)
    )
    if not rows:
        return
    for (role_id,) in rows:
        role = guild.get_role(role_id)
        if role is None:
            continue
        try:
            await role.delete(reason=f"Evento {event_id} eliminato")
        except (discord.Forbidden, discord.HTTPException):
            pass

async def assign_lobby_roles(event_id: int, lobby_id: int, guild: discord.Guild):
    role_id = await get_lobby_role(event_id, lobby_id)
    if role_id is None:
        raise ValueError("role not set")
    role = guild.get_role(role_id)
    if role is None:
        raise ValueError("role doesn't exist")
    leaders = await get_leader_ids(event_id, lobby_id)
    for l_id in leaders:
        leader = guild.get_member(l_id)
        if leader is None:
            continue
        if role in leader.roles:
            continue
        try:
            await leader.add_roles(role)
        except discord.Forbidden:
            raise PermissionError("bot has not permission to assign roles")
        except discord.HTTPException:
            continue

async def lock_channel_for_lobby(
    channel: discord.TextChannel,
    role: discord.Role
):
    await channel.set_permissions(
        channel.guild.default_role,
        view_channel=False
    )

    await channel.set_permissions(
        role,
        view_channel=True,
        send_messages=False,
        read_message_history=True
    )


async def assign_user_lobby_role(
    event_id: int,
    lobby_id: int,
    user_id: int,
    guild: discord.Guild
):
    role_id = await get_lobby_role(event_id, lobby_id)

    if role_id is None:
        raise ValueError("Lobby role not found")

    role = guild.get_role(role_id)

    if role is None:
        raise ValueError("Discord role does not exist")

    member = guild.get_member(user_id)

    if member is None:
        raise ValueError("User is not in the guild")

    if role in member.roles:
        return

    await member.add_roles(
        role,
        reason=f"Assegnazione ruolo lobby {lobby_id} evento {event_id}"
    )


async def remove_user_lobby_role(
    event_id: int,
    lobby_id: int,
    user_id: int,
    guild: discord.Guild
):
    role_id = await get_lobby_role(event_id, lobby_id)

    if role_id is None:
        return

    role = guild.get_role(role_id)

    if role is None:
        return

    member = guild.get_member(user_id)

    if member is None:
        return

    if role in member.roles:
        await member.remove_roles(
            role,
            reason=f"Rimozione ruolo lobby {lobby_id} evento {event_id}"
        )

async def check_event_config_complete(event_id: int, guild_id: int) -> list[str]:
    missing: list[str] = []
    row = await fetch_one(
        "SELECT ranking_channel_id, admin_role_id, live_ranking_channel_id, lobbies_channel_id FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )
    if row is None:
        missing.extend(["Canale classifiche", "Ruolo admin", "Canale classifiche live", "Canale lobby"])
    else:
        for rc_id, ar_id, lrc_id, lc_id in row:
            if rc_id is None:
                missing.append("Canale classifiche")
            if ar_id is None:
                missing.append("Ruolo admin")
            if lrc_id is None:
                missing.append("Canale classifiche live")
            if lc_id is None:
                missing.append("Canale lobby")
    lobby_codes_channels = await get_lobby_codes_channels(event_id)
    if lobby_codes_channels is None:
        missing.append("Canali codici lobby")
    return missing
