import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
PG_DSN = os.getenv("PG_DSN")
REDIS_URL = os.getenv("REDIS_URL")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not DISCORD_TOKEN or GUILD_ID == 0 or not PG_DSN or not REDIS_URL:
    raise RuntimeError("Variables d'environnement manquantes: DISCORD_TOKEN, GUILD_ID, PG_DSN, REDIS_URL")
