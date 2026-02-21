import json
import io
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from db import backup_all_data
from config import ADMIN_USER_ID

def serialize_row(row):
    """تبدیل رکورد دیتابیس به دیکشنری و تبدیل datetime به رشته"""
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime,)):
            d[k] = v.isoformat()
    return d

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /backup برای گرفتن بکاپ دیتابیس و ارسال فایل JSON"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("⏳ در حال گرفتن بکاپ...")

    try:
        # بکاپ در دیتابیس
        await backup_all_data(context.application.db)

        # آماده‌سازی فایل JSON
        async with context.application.db.acquire() as conn:
            videos = await conn.fetch("SELECT * FROM videos")
            media_groups = await conn.fetch("SELECT * FROM media_groups")

        backup_data = {
            "videos": [serialize_row(v) for v in videos],
            "media_groups": [serialize_row(m) for m in media_groups],
        }

        json_bytes = io.BytesIO()
        json_bytes.write(json.dumps(backup_data, ensure_ascii=False, indent=2).encode("utf-8"))
        json_bytes.seek(0)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=json_bytes,
            filename="backup.json",
            caption="✅ بکاپ دیتابیس و مدیا گروپ‌ها"
        )

        await update.message.reply_text("✅ بکاپ با موفقیت گرفته شد!")

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در گرفتن بکاپ: {e}")


async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /restore برای بازگردانی داده‌ها از فایل JSON"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    if not update.message.document:
        await update.message.reply_text("❌ لطفاً فایل JSON بکاپ را ارسال کنید")
        return

    await update.message.reply_text("⏳ در حال بازگردانی داده‌ها از فایل JSON...")

    try:
        file = await context.bot.get_file(update.message.document.file_id)
        file_bytes = await file.download_as_bytearray()
        backup_data = json.loads(file_bytes)

        async with context.application.db.acquire() as conn:
            # پاک کردن داده‌های قدیمی
            await conn.execute("TRUNCATE videos, media_groups RESTART IDENTITY;")

            # بازگردانی ویدیوها
            for v in backup_data.get("videos", []):
                await conn.execute("""
                    INSERT INTO videos (message_id, file_id, title, caption, deep_link, thumbnail_file_id, created_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                    ON CONFLICT (message_id) DO NOTHING
                """, v["message_id"], v["file_id"], v["title"], v["caption"], v["deep_link"], v.get("thumbnail_file_id"), v["created_at"])

            # بازگردانی مدیا گروپ‌ها
            for m in backup_data.get("media_groups", []):
                await conn.execute("""
                    INSERT INTO media_groups (key, file_id, deep_link, created_at)
                    VALUES ($1,$2,$3,$4)
                    ON CONFLICT (key, file_id) DO NOTHING
                """, m["key"], m["file_id"], m["deep_link"], m["created_at"])

        await update.message.reply_text("✅ داده‌ها با موفقیت بازگردانی شدند!")

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در بازگردانی: {e}")
