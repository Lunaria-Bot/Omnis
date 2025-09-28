import asyncpg

_pool = None

async def init_db(dsn: str):
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        # Exécuter le schéma au démarrage
        with open("schema.sql", "r", encoding="utf-8") as f:
            await conn.execute(f.read())

def pool():
    if _pool is None:
        raise RuntimeError("DB non initialisée")
    return _pool
