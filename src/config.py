import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# On force LOG_LEVEL à une valeur valide
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    LOG_LEVEL = "INFO"  # fallback par défaut

if not DISCORD_TOKEN or GUILD_ID == 0 or not DATABASE_URL or not REDIS_URL:
    raise RuntimeError(
        "Variables d'environnement manquantes: DISCORD_TOKEN, GUILD_ID, DATABASE_URL, REDIS_URL"
    )
