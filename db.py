import asyncpg
from datetime import datetime
# ========================== Backup & Restore ==========================

BACKUP_VIDEOS_TABLE = "videos_backup"
BACKUP_MEDIA_GROUP_TABLE = "media_groups_backup"

async def init_backup_tables(pool):
    """ایجاد جداول بکاپ اگر وجود نداشت"""
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {BACKUP_VIDEOS_TABLE} AS TABLE {DB_TABLE} WITH NO DATA;
        """)
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {BACKUP_MEDIA_GROUP_TABLE} AS TABLE {MEDIA_GROUP_TABLE} WITH NO DATA;
        """)

async def backup_all_data(pool):
    """تمام ویدیوها و مدیا گروپ‌ها را در جداول بکاپ ذخیره می‌کند"""
    async with pool.acquire() as conn:
        # پاک کردن داده‌های قدیمی
        await conn.execute(f"TRUNCATE {BACKUP_VIDEOS_TABLE}, {BACKUP_MEDIA_GROUP_TABLE} RESTART IDENTITY;")

        # ویدیوها
        await conn.execute(f"""
            INSERT INTO {BACKUP_VIDEOS_TABLE} (message_id, file_id, title, caption, deep_link, thumbnail_file_id, created_at)
            SELECT message_id, file_id, title, caption, deep_link, thumbnail_file_id, created_at
            FROM {DB_TABLE};
        """)

        # مدیا گروپ‌ها
        await conn.execute(f"""
            INSERT INTO {BACKUP_MEDIA_GROUP_TABLE} (key, file_id, deep_link, created_at)
            SELECT key, file_id, deep_link, created_at
            FROM {MEDIA_GROUP_TABLE};
        """)

async def restore_from_backup(pool):
    """داده‌های بکاپ را به جداول اصلی برمی‌گرداند"""
    async with pool.acquire() as conn:
        # ویدیوها
        await conn.execute(f"""
            INSERT INTO {DB_TABLE} (message_id, file_id, title, caption, deep_link, thumbnail_file_id, created_at)
            SELECT message_id, file_id, title, caption, deep_link, thumbnail_file_id, created_at
            FROM {BACKUP_VIDEOS_TABLE}
            ON CONFLICT (message_id) DO NOTHING;
        """)

        # مدیا گروپ‌ها
        await conn.execute(f"""
            INSERT INTO {MEDIA_GROUP_TABLE} (key, file_id, deep_link, created_at)
            SELECT key, file_id, deep_link, created_at
            FROM {BACKUP_MEDIA_GROUP_TABLE}
            ON CONFLICT (key, file_id) DO NOTHING;
        """)
