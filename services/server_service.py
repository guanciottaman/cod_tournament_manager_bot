import sqlite3
import discord
from db.db import *

async def check_server_registered(guild_id: int) -> bool:
    exists = await fetch_one(
        "SELECT 1 FROM server_configs WHERE guild_id = ?",
        (guild_id,)
    )

    return exists is not None

async def create_server_config(guild_id: int, ranking_channel_id: int, admin_role_id: int) -> bool:

    try:
        await execute("""
            INSERT INTO server_configs
            (guild_id, ranking_channel_id, admin_role_id)
            VALUES (?, ?, ?)
        """, (guild_id, ranking_channel_id, admin_role_id))

        return True

    except sqlite3.IntegrityError:
        return False

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