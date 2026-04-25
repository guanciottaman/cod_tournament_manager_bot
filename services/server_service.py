import sqlite3

from db.db import *

async def check_server_registered(guild_id: int) -> bool:
    exists = await fetch_one("SELECT 1 FROM server_configs WHERE guild_id = ?", (guild_id,))
    return True if exists else False

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