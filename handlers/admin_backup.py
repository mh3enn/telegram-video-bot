import json
from telegram import Update
from telegram.ext import ContextTypes
from io import BytesIO

from db import backup_all_data, restore_from_backup
from config import ADMIN_GROUP_ID

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /backup برای گرفتن بکاپ دیتابیس و ارسال فایل JSON"""
    if update.effective_user.id != ADMIN_GROUP_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("⏳ در حال گرفتن بکاپ...")

    try:
        # گرفتن داده‌های بکاپ از دیتابیس
        backup_data = await backup_all_data(context.application.db)

        # تبدیل به JSON
        backup_json = json.dumps(backup_data, default=str, ensure_ascii=False)

        # آماده کردن فایل برای ارسال
        bio = BytesIO(backup_json.encode("utf-8"))
        bio.name = "backup.json"

        # ارسال فایل
        await update.message.reply_document(
            document=bio,
            caption="✅ بکاپ دیتابیس با موفقیت آماده شد"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در گرفتن بکاپ: {e}")


async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگردانی بکاپ وقتی فایل JSON فرستاده شد"""
    msg = update.message
    if not msg:
        return

    if msg.from_user.id != ADMIN_GROUP_ID:
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
