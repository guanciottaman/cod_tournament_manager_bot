import aiosqlite

DB_PATH = "db.sqlite3"

async def fetch_one(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()

async def fetch_all(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()

async def execute(query: str, params: tuple = ()):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid