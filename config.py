import os

def get_int_env(name: str, default: int | None = None) -> int:
    value = os.getenv(name)
    if value is None:
        if default is None:
            raise RuntimeError(f"Environment variable {name} is not set")
        return default
    return int(value)

# ===== Bot & Environment =====
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

ADMIN_GROUP_ID = get_int_env("ADMIN_GROUP_ID")
BOT_ADMIN_ID = get_int_env("BOT_ADMIN_ID", 0)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# ===== Sponsor Channels =====
SPONSOR_CHANNELS = [
    "@fansonly90775",
    "@Fansonly_TG"
]

CHANNEL_TITLES = {
    "@fansonly90775": "📢 عضویت در کانال اصلی",
    "@Fansonly_TG": "📢 عضویت در کانال پشتیبان",
}

CHANNEL_INVITES = {}

# ===== Cache =====
CACHE_TTL = 300  # seconds
