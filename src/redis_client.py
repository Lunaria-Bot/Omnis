import redis.asyncio as redis

_client = None

async def init_redis(url: str):
    global _client
    _client = redis.from_url(url, encoding="utf-8", decode_responses=True)

def rds():
    if _client is None:
        raise RuntimeError("Redis non initialisé")
    return _client
