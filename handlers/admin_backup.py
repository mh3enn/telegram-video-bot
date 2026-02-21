import json
from datetime import datetime
import io 

from telegram import Update
from telegram.ext import ContextTypes

from db import restore_from_backup
from config import ADMIN_USER_ID


def serialize_row(row):
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


# ---------------- BACKUP ----------------

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("⏳ در حال گرفتن بکاپ...")

    try:
        async with context.application.db.acquire() as conn:
            videos = await conn.fetch("SELECT * FROM videos")
            media_groups = await conn.fetch("SELECT * FROM media_groups")

        backup_data = {
            "videos": [serialize_row(v) for v in videos],
            "media_groups": [serialize_row(m) for m in media_groups],
        }

        json_bytes = BytesIO()
        json_bytes.write(
            json.dumps(backup_data, ensure_ascii=False, indent=2).encode("utf-8")
        )
        json_bytes.seek(0)

        await update.message.reply_document(
            document=json_bytes,
            filename="backup.json",
            caption="✅ بکاپ دیتابیس"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در گرفتن بکاپ: {e}")


# ---------------- RESTORE STEP 1 ----------------

async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("📂 لطفاً فایل backup.json را ارسال کنید.")


# ---------------- RESTORE STEP 2 ----------------

async def handle_restore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or not msg.document:
        return

    if msg.from_user.id != ADMIN_USER_ID:
        return

    if not msg.document.file_name.endswith(".json"):
        return

    await msg.reply_text("⏳ در حال بازگردانی داده‌ها...")

    try:
        file = await context.bot.get_file(msg.document.file_id)
        file_bytes = await file.download_as_bytearray()
        backup_data = json.loads(file_bytes)

        await restore_from_backup(context.application.db, backup_data)

        await msg.reply_text("✅ ریستور با موفقیت انجام شد!")

    except Exception as e:
        await msg.reply_text(f"❌ خطا در بازگردانی: {e}")            "media_groups": [serialize_row(m) for m in media_groups],
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
    """بازگردانی بکاپ وقتی فایل JSON فرستاده شد"""
    msg = update.message
    if not msg:
        return

    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    if not msg.document:
        await msg.reply_text("❌ لطفاً فایل JSON بکاپ را ارسال کنید")
        return

    if not msg.document.file_name.endswith(".json"):
        await msg.reply_text("❌ فایل باید با فرمت .json باشد")
        return

    await msg.reply_text("⏳ در حال بازگردانی داده‌ها از فایل JSON...")

    try:
        # دانلود فایل
        file = await context.bot.get_file(msg.document.file_id)
        file_bytes = await file.download_as_bytearray()
        backup_data = json.loads(file_bytes)

        # بازگردانی داده‌ها به دیتابیس
        await restore_from_backup(context.application.db, backup_data)
        await msg.reply_text("✅ داده‌ها با موفقیت بازگردانی شدند!")
    except Exception as e:
        await msg.reply_text(f"❌ خطا در بازگردانی: {e}")
