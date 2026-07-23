import asyncpg
from asyncpg import Pool

from typing import Any

from config.config import DB_USER, DB_PASSWORD, DB, DB_HOST

pool: Pool | None = None

async def init_db():
    global pool

    pool = await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB,
        host=DB_HOST,
        min_size=2,
        max_size=10
    )

def get_pool() -> Pool:
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    return pool

async def close_db():
    global pool

    if pool is not None:
        await pool.close()
        pool = None

async def fetch_one(query: str, params: tuple[Any, ...] = tuple()):
    async with get_pool() as conn:
        return await conn.fetchrow(query, *params)


async def fetch_all(query: str, params: tuple[Any, ...] = tuple()):
    async with get_pool() as conn:
        return await conn.fetch(query, *params)


async def execute(query: str, params: tuple[Any, ...] = tuple()):
    async with get_pool() as conn:
        return await conn.execute(query, *params)