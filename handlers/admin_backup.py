from telegram import Update
from telegram.ext import ContextTypes
from db import backup_all_data, restore_from_backup
from config import ADMIN_GROUP_ID

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /backup برای گرفتن بکاپ دیتابیس"""
    if update.effective_user.id != ADMIN_GROUP_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("⏳ در حال گرفتن بکاپ...")
    try:
        await backup_all_data(context.application.db)
        await update.message.reply_text("✅ بکاپ با موفقیت گرفته شد!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در گرفتن بکاپ: {e}")

async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر /restore برای بازگردانی داده‌ها از بکاپ"""
    if update.effective_user.id != ADMIN_GROUP_ID:
        await update.message.reply_text("❌ دسترسی ندارید")
        return

    await update.message.reply_text("⏳ در حال بازگردانی داده‌ها از بکاپ...")
    try:
        await restore_from_backup(context.application.db)
        await update.message.reply_text("✅ داده‌ها با موفقیت بازگردانی شدند!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در بازگردانی: {e}")
