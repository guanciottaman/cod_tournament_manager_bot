import sqlite3
import discord

from typing import Any

from models.server_config import ServerConfig
from db.db import *

blacklist_cache: dict[int, dict[str, Any]] = {}

async def check_server_registered(guild_id: int) -> bool:
    exists = await fetch_one(
        "SELECT 1 FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )

    return exists is not None

async def create_server_config(
    guild_id: int,
    ranking_channel_id: int,
    admin_role_id: int,
    live_ranking_channel_id: int,
    lobbies_channel_id: int
) -> bool:
    try:
        await execute("""
            INSERT INTO server_configs
            (guild_id, ranking_channel_id, admin_role_id, live_ranking_channel_id, lobbies_channel_id)
            VALUES (?, ?, ?, ?, ?)
        """, (guild_id, ranking_channel_id, admin_role_id, live_ranking_channel_id, lobbies_channel_id))

        return True

    except sqlite3.IntegrityError:
        return False

async def get_server_config(guild_id: int) -> ServerConfig | None:
    server_config = await fetch_one(
        "SELECT ranking_channel_id, admin_role_id, live_ranking_channel_id, lobbies_channel_id FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )
    if not server_config:
        return None
    return ServerConfig(
        guild_id,
        server_config[0],
        server_config[1],
        server_config[2],
        server_config[3]
    )

async def edit_server_config(
    guild_id: int,
    ranking_channel_id: int | None = None,
    admin_role_id: int | None = None,
    live_ranking_channel_id: int | None = None,
    lobbies_channel_id: int | None = None
) -> None:
    updates: list[str] = []
    params: list[int] = []

    if ranking_channel_id is not None:
        updates.append("ranking_channel_id = ?")
        params.append(ranking_channel_id)

    if admin_role_id is not None:
        updates.append("admin_role_id = ?")
        params.append(admin_role_id)

    if live_ranking_channel_id is not None:
        updates.append("live_ranking_channel_id = ?")
        params.append(live_ranking_channel_id)
    
    if lobbies_channel_id is not None:
        updates.append("lobbies_channel_id = ?")
        params.append(lobbies_channel_id)

    if not updates:
        return

    params.append(guild_id)

    await execute(
        f"""
        UPDATE server_configs
        SET {", ".join(updates)}
        WHERE guild_id = ?
        """,
        tuple(params)
    )

async def delete_server_config(guild_id: int):
    await execute(
        "DELETE FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )

async def get_admin_role_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT admin_role_id FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )

    if row:
        return row[0]
    else:
        return None

async def get_ranking_channel_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT ranking_channel_id FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )
    if row:
        return row[0]
    else:
        return None

async def get_live_ranking_channel_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT live_ranking_channel_id FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )
    if row:
        return row[0]
    else:
        return None

async def get_lobbies_channel_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT lobbies_channel_id FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )
    if row:
        return row[0]
    else:
        return None

async def check_admin_role(interaction: discord.Interaction):
    admin_role_id = await get_admin_role_id(interaction.guild_id)
    if not admin_role_id:
        return False

    admin_role = interaction.guild.get_role(admin_role_id)
    if admin_role is None:
        return False
    return admin_role in interaction.user.roles


async def get_blacklisted_servers() -> set[int]:
    blacklisted_servers = await fetch_all(
        "SELECT guild_id FROM blacklisted_servers"
    )
    return set(b[0] for b in blacklisted_servers)

async def get_blacklist() -> dict[int, dict[str, Any]]:
    rows = await fetch_all(
        "SELECT guild_id, blacklisted_at, blacklisted_by FROM blacklisted_servers"
    )

    return {
        row[0]: {
            "blacklisted_at": row[1],
            "blacklisted_by": row[2]
        }
        for row in rows
    }

async def init_blacklist_cache():
    global blacklist_cache

    rows = await fetch_all(
        "SELECT guild_id, blacklisted_at, blacklisted_by FROM blacklisted_servers"
    )

    blacklist_cache = {
        row[0]: {
            "blacklisted_at": row[1],
            "blacklisted_by": row[2]
        }
        for row in rows
    }

def is_blacklisted(guild_id: int) -> bool:
    return guild_id in blacklist_cache

async def reload_blacklist_cache():
    await init_blacklist_cache()

async def blacklist_guild(guild_id: int, by: int):
    await execute(
        """
        INSERT OR REPLACE INTO blacklisted_servers
        (guild_id, blacklisted_at, blacklisted_by)
        VALUES (?, CURRENT_TIMESTAMP, ?)
        """,
        (guild_id, by)
    )

    row = await fetch_one(
        "SELECT blacklisted_at FROM blacklisted_servers WHERE guild_id = ?",
        (guild_id,)
    )
    if row is None:
        return

    blacklist_cache[guild_id] = {
        "blacklisted_at": row[0],
        "blacklisted_by": by
    }

async def unblacklist_guild(guild_id: int):
    await execute(
        "DELETE FROM blacklisted_servers WHERE guild_id = ?",
        (guild_id,)
    )

    blacklist_cache.pop(guild_id, None)