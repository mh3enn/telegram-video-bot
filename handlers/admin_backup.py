import json
import io
from telegram import Update
from telegram.ext import ContextTypes
from db import backup_all_data, restore_from_backup, get_video_record, get_media_group
from config import ADMIN_USER_ID
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /backup برای گرفتن بکاپ دیتابیس و ارسال فایل JSON"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("⏳ در حال گرفتن بکاپ در دیتابیس و آماده‌سازی فایل JSON...")

    try:
        # ۱️⃣ بکاپ در دیتابیس
        await backup_all_data(context.application.db)

        # ۲️⃣ آماده‌سازی فایل JSON
        async with context.application.db.acquire() as conn:
            videos = await conn.fetch("SELECT * FROM videos")
            media_groups = await conn.fetch("SELECT * FROM media_groups")

        backup_data = {
            "videos": [dict(v) for v in videos],
            "media_groups": [dict(m) for m in media_groups],
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
    """هندلر /restore برای بازگردانی داده‌ها از بکاپ"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("⏳ در حال بازگردانی داده‌ها از بکاپ دیتابیس...")

    try:
        await restore_from_backup(context.application.db)
        await update.message.reply_text("✅ داده‌ها با موفقیت بازگردانی شدند!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در بازگردانی: {e}")
