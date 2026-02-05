import asyncpg

DB_TABLE = "videos"

async def init_db(application, database_url: str):
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    application.db = pool
    await init_db_schema(pool)


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
