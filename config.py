import os

# ===== Bot & Environment =====
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_ADMIN_ID = int(os.getenv("BOT_ADMIN_ID", "0"))

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
