import asyncpg
from src.config import DATABASE_URL

_pool = None

async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        with open("schema.sql", "r", encoding="utf-8") as f:
            await conn.execute(f.read())

def pool():
    if _pool is None:
        raise RuntimeError("DB non initialisée")
    return _pool
