import discord
import asyncpg
import logging

from typing import Any

from models.server_config import ServerConfig
from db.db import *

logger = logging.getLogger(__name__)

blacklist_cache: dict[int, dict[str, Any]] = {}

async def check_server_registered(guild_id: int) -> bool:
    exists = await fetch_one(
        "SELECT 1 FROM server_configs WHERE guild_id = $1",
        (guild_id,)
    )

    return exists is not None

async def set_panel_channel_id(guild_id: int, channel_id: int):
    await execute(
        "UPDATE server_configs SET panel_channel_id = $1 WHERE guild_id = $2",
        (channel_id, guild_id)
    )

async def get_panel_channel_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT panel_channel_id FROM server_configs WHERE guild_id = $1",
        (guild_id,)
    )
    return row["panel_channel_id"] if row is not None else None

async def create_server_config(
    guild_id: int,
    config: ServerConfig
) -> bool:
    try:
        await execute("""
            INSERT INTO server_configs
            (guild_id, ranking_channel_id, admin_role_id, live_ranking_channel_id, lobbies_channel_id)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, (
                guild_id,
                config.ranking_channel_id,
                config.admin_role_id,
                config.live_ranking_channel_id,
                config.lobbies_channel_id
            )
        )

        return True

    except asyncpg.UniqueViolationError:
        return False

async def get_server_config(guild_id: int) -> ServerConfig | None:
    server_config = await fetch_one(
        """
            SELECT
                panel_channel_id,
                ranking_channel_id,
                admin_role_id,
                live_ranking_channel_id,
                lobbies_channel_id
            FROM server_configs
            WHERE guild_id = $1
        """,
        (guild_id,)
    )
    if not server_config:
        return None
    return ServerConfig(
        guild_id,
        server_config["ranking_channel_id"],
        server_config["admin_role_id"],
        server_config["live_ranking_channel_id"],
        server_config["lobbies_channel_id"]
    )

async def edit_server_config(
    guild_id: int,
    config: ServerConfig
) -> None:
    updates: list[str] = []
    params: list[int] = []

    if config.ranking_channel_id is not None:
        params.append(config.ranking_channel_id)
        updates.append(f"ranking_channel_id = ${len(params)}")

    if config.admin_role_id is not None:
        params.append(config.admin_role_id)
        updates.append(f"admin_role_id = ${len(params)}")

    if config.live_ranking_channel_id is not None:
        params.append(config.live_ranking_channel_id)
        updates.append(f"live_ranking_channel_id = ${len(params)}")

    if config.lobbies_channel_id is not None:
        params.append(config.lobbies_channel_id)
        updates.append(f"lobbies_channel_id = ${len(params)}")

    if not updates:
        return

    params.append(guild_id)

    await execute(
        f"""
        UPDATE server_configs
        SET {", ".join(updates)}
        WHERE guild_id = ${len(params)}
        """,
        tuple(params)
    )

async def delete_server_config(guild_id: int):
    await execute(
        "DELETE FROM server_configs WHERE guild_id = $1",
        (guild_id,)
    )

async def get_admin_role_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT admin_role_id FROM server_configs WHERE guild_id = $1",
        (guild_id,)
    )

    if row:
        return row["admin_role_id"]
    else:
        return None

async def get_ranking_channel_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT ranking_channel_id FROM server_configs WHERE guild_id = $1",
        (guild_id,)
    )
    if row:
        return row["ranking_channel_id"]
    else:
        return None

async def get_live_ranking_channel_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT live_ranking_channel_id FROM server_configs WHERE guild_id = $1",
        (guild_id,)
    )
    if row:
        return row["live_ranking_channel_id"]
    else:
        return None

async def get_lobbies_channel_id(guild_id: int) -> int | None:
    row = await fetch_one(
        "SELECT lobbies_channel_id FROM server_configs WHERE guild_id = $1",
        (guild_id,)
    )
    if row:
        return row["lobbies_channel_id"]
    else:
        return None

async def check_admin_role(interaction: discord.Interaction):
    if interaction.guild is None:
        return False
    admin_role_id = await get_admin_role_id(interaction.guild.id)
    if not admin_role_id:
        return False
    admin_role = interaction.guild.get_role(admin_role_id)
    if admin_role is None:
        return False
    if not interaction.user or not isinstance(interaction.user, discord.Member):
        return False
    return admin_role in interaction.user.roles


async def get_blacklisted_servers() -> set[int]:
    blacklisted_servers = await fetch_all(
        "SELECT guild_id FROM blacklisted_servers"
    )
    return set(b["guild_id"] for b in blacklisted_servers)

async def get_blacklist() -> dict[int, dict[str, Any]]:
    rows = await fetch_all(
        "SELECT guild_id, blacklisted_at, blacklisted_by FROM blacklisted_servers"
    )

    return {
        row["guild_id"]: {
            "blacklisted_at": row["blacklisted_at"],
            "blacklisted_by": row["blacklisted_by"]
        }
        for row in rows
    }

async def init_blacklist_cache():
    global blacklist_cache

    rows = await fetch_all(
        "SELECT guild_id, blacklisted_at, blacklisted_by FROM blacklisted_servers"
    )

    blacklist_cache = {
        row["guild_id"]: {
            "blacklisted_at": row["blacklisted_at"],
            "blacklisted_by": row["blacklisted_by"]
        }
        for row in rows
    }

def is_blacklisted(guild_id: int) -> bool:
    return guild_id in blacklist_cache

async def reload_blacklist_cache():
    await init_blacklist_cache()

async def blacklist_guild(guild_id: int, by: int):
    row = await fetch_one(
        """
        INSERT INTO blacklisted_servers
        (guild_id, blacklisted_by)
        VALUES ($1, $2)
        ON CONFLICT (guild_id)
        DO UPDATE SET
            blacklisted_at = CURRENT_TIMESTAMP,
            blacklisted_by = EXCLUDED.blacklisted_by
        RETURNING blacklisted_at, blacklisted_by
        """,
        (guild_id, by)
    )
    logging.info(row)
    if row is None:
        logger.error(f"Failed to blacklist guild {guild_id}. No row returned from database.")
        return

    blacklist_cache[guild_id] = {
        "blacklisted_at": row["blacklisted_at"],
        "blacklisted_by": row["blacklisted_by"]
    }

async def unblacklist_guild(guild_id: int):
    await execute(
        "DELETE FROM blacklisted_servers WHERE guild_id = $1",
        (guild_id,)
    )

    blacklist_cache.pop(guild_id, None)

async def check_bot_permissions(guild: discord.Guild) -> list[str]:
    me = guild.me
    

    required = {
        "view_channel": "Visualizzare i canali",
        "send_messages": "Inviare messaggi",
        "embed_links": "Incorporare i link",
        "read_message_history": "Leggere la cronologia messaggi",
        "manage_roles": "Gestire i ruoli",
        "manage_channels": "Gestire i canali",
        "use_application_commands": "Usare gli slash command",
    }
    if not me:
        return list(required.values())

    missing: list[str] = []

    perms = me.guild_permissions

    for attr, label in required.items():
        if not getattr(perms, attr):
            missing.append(label)

    return missing

async def check_channel_permissions(
    channel: discord.abc.GuildChannel,
    guild: discord.Guild,
    required: dict[str, str]
) -> list[str]:
    me = guild.me
    if not me:
        return ["Non puoi usarmi dai DM"]

    perms = channel.permissions_for(me)

    missing: list[str] = []

    for attr, label in required.items():
        if not getattr(perms, attr):
            missing.append(label)

    return missing