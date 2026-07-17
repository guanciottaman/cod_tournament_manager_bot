import asyncpg
from asyncpg import Pool

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

async def fetch_one(query: str, params: tuple = tuple()):
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *params)


async def fetch_all(query: str, params: tuple = tuple()):
    async with pool.acquire() as conn:
        return await conn.fetch(query, *params)


async def execute(query: str, params: tuple = tuple()):
    async with pool.acquire() as conn:
        return await conn.execute(query, *params)