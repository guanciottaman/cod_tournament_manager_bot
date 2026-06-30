import sqlite3
import discord

from models.server_config import ServerConfig
from db.db import *

async def check_server_registered(guild_id: int) -> bool:
    exists = await fetch_one(
        "SELECT 1 FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )

    return exists is not None

async def create_server_config(guild_id: int, ranking_channel_id: int, admin_role_id: int, live_ranking_channel_id: int) -> bool:
    try:
        await execute("""
            INSERT INTO server_configs
            (guild_id, ranking_channel_id, admin_role_id, live_ranking_channel_id)
            VALUES (?, ?, ?, ?)
        """, (guild_id, ranking_channel_id, admin_role_id, live_ranking_channel_id))

        return True

    except sqlite3.IntegrityError:
        return False

async def get_server_config(guild_id: int) -> ServerConfig | None:
    server_config = await fetch_one(
        "SELECT ranking_channel_id, admin_role_id, live_ranking_channel_id FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )
    if not server_config:
        return None
    return ServerConfig(
        guild_id,
        server_config[0],
        server_config[1],
        server_config[2]
    )

async def edit_server_config(
    guild_id: int,
    ranking_channel_id: int | None = None,
    admin_role_id: int | None = None,
    live_ranking_channel_id: int | None = None
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

async def check_admin_role(interaction: discord.Interaction):
    admin_role_id = await get_admin_role_id(interaction.guild_id)
    if not admin_role_id:
        return False

    admin_role = interaction.guild.get_role(admin_role_id)
    if admin_role is None:
        return False
    return admin_role in interaction.user.roles