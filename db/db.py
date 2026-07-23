import asyncpg
from asyncpg import Pool

from typing import Any
import logging

from config.config import DB_USER, DB_PASSWORD, DB, DB_HOST


logger = logging.getLogger(__name__)

pool: Pool | None = None

async def init_db():
    global pool

    logging.info("Creating db...")

    pool = await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB,
        host=DB_HOST,
        min_size=2,
        max_size=10
    )

    logging.info(f"Pool created: {pool}")

def get_pool() -> Pool:
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    return pool


async def close_db():
    global pool

    logging.info("Closing db...")

    if pool:
        await pool.close()
        pool = None

async def fetch_one(query: str, params: tuple[Any, ...] = tuple()):
    async with get_pool().acquire() as conn:
        return await conn.fetchrow(query, *params)


async def fetch_all(query: str, params: tuple[Any, ...] = tuple()):
    async with get_pool().acquire() as conn:
        return await conn.fetch(query, *params)


async def execute(query: str, params: tuple[Any, ...] = tuple()):
    async with get_pool().acquire() as conn:
        return await conn.execute(query, *params)