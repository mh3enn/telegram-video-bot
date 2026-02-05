import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from db import get_video_record, log_download
from cache import get_cached_membership, set_cached_membership
from utils import build_join_keyboard, build_missing_text,delete_after_delay
from config import SPONSOR_CHANNELS


async def check_user_membership(bot, user_id, use_cache=True):
    if use_cache:
        cached = get_cached_membership(user_id)
        if cached is not None:
            return cached

    missing = []
    for ch in SPONSOR_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except Exception:
            missing.append(ch)

    if use_cache:
        set_cached_membership(user_id, missing)

    return missing
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "👋 سلام!\n\n"
            "📥 این ربات برای دریافت ویدیوها استفاده می‌شود.\n"
            "🔗 لطفاً برای دریافت فیلم عضو کانال زیر شوید\n\n"
            "@Fansonly_TG"
        )
        return

    key = context.args[0]
    row = await get_video_record(context.application.db, key)
    if not row:
        await update.message.reply_text("❌ فایل موردنظر پیدا نشد")
        return

    user_id = update.effective_user.id
    bot = context.bot

    missing = await check_user_membership(bot, user_id)

    if not missing:
        msg = await bot.send_video(
            chat_id=update.effective_chat.id,
            video=row["file_id"],
            caption=(
                "📥 این فایل را در Saved Messages ذخیره کنید\n"
                "⏱ فایل بعد از ۳۰ ثانیه حذف می‌شود\n\n"
                "@Fansonly_TG"
            )
        )

        await log_download(context.application.db, key, user_id)

        asyncio.create_task(
            delete_after_delay(bot, update.effective_chat.id, msg.message_id)
        )
        return

    kb = await build_join_keyboard(bot, missing, key)
    text = build_missing_text(len(missing))

    await bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=kb
  )
