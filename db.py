import asyncpg
from datetime import datetime

DB_TABLE = "videos"
MEDIA_GROUP_TABLE = "media_groups"  # جدول برای media group

async def init_db(application, database_url: str):
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    application.db = pool
    await init_db_schema(pool)
    await init_media_group_table(pool)  # اضافه شد

# ========================== Videos ==========================
async def init_db_schema(pool):
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {DB_TABLE} (
                id SERIAL PRIMARY KEY,
                message_id TEXT UNIQUE,
                file_id TEXT NOT NULL,
                title TEXT,
                caption TEXT,
                deep_link TEXT,
                thumbnail_file_id TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS download_logs (
                id SERIAL PRIMARY KEY,
                video_key TEXT,
                user_id BIGINT,
                downloaded_at TIMESTAMPTZ DEFAULT now()
            );
        """)

async def save_video_record(
    pool,
    message_id,
    file_id,
    title,
    caption,
    deep_link,
    thumbnail_file_id=None
):
    if not message_id:
        raise ValueError("message_id is required")
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            f"""
            INSERT INTO {DB_TABLE}
            (message_id, file_id, title, caption, deep_link, thumbnail_file_id)
            VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT (message_id) DO UPDATE
            SET
                file_id = EXCLUDED.file_id,
                title = EXCLUDED.title,
                caption = EXCLUDED.caption,
                deep_link = EXCLUDED.deep_link,
                thumbnail_file_id = EXCLUDED.thumbnail_file_id
            RETURNING id, message_id;
            """,
            str(message_id),
            file_id,
            title,
            caption,
            deep_link,
            thumbnail_file_id,
        )

async def get_video_record(pool, message_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            f"SELECT * FROM {DB_TABLE} WHERE message_id = $1",
            str(message_id),
        )

async def log_download(pool, video_key, user_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO download_logs (video_key, user_id) VALUES ($1, $2)",
            video_key,
            user_id,
        )

async def get_total_videos(pool):
    async with pool.acquire() as conn:
        return await conn.fetchval(f"SELECT COUNT(*) FROM {DB_TABLE}")

async def get_total_downloads(pool):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM download_logs")

async def get_today_downloads(pool):
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM download_logs WHERE downloaded_at::date = CURRENT_DATE"
        )

# ========================== Media Group ==========================
async def init_media_group_table(pool):
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {MEDIA_GROUP_TABLE} (
                id SERIAL PRIMARY KEY,
                media_group_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                deep_link TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE(media_group_id, file_id)
            );
        """)

async def save_media_group(pool, media_group_id, file_ids, deep_link):
    """
    ذخیره media group در دیتابیس
    file_ids: list[str]
    """
    async with pool.acquire() as conn:
        for file_id in file_ids:
            await conn.execute(
                f"""
                INSERT INTO {MEDIA_GROUP_TABLE} (media_group_id, file_id, deep_link, created_at)
                VALUES ($1,$2,$3,now())
                ON CONFLICT (media_group_id, file_id) DO NOTHING
                """,
                media_group_id,
                file_id,
                deep_link
        )
