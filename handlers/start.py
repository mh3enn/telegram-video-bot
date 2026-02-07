import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes

from db import get_video_record, log_download, get_media_group
from cache import get_cached_membership, set_cached_membership
from utils import build_join_keyboard, build_missing_text, delete_after_delay
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
    bot = context.bot
    user_id = update.effective_user.id

    # ================== اول بررسی عضویت ==================
    missing = await check_user_membership(bot, user_id)

    if missing:
        kb = await build_join_keyboard(bot, missing, key)
        text = build_missing_text(len(missing))
        await bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=kb
        )
        return

    # ================== VIDEO ==================
    row = await get_video_record(context.application.db, key)
    if row:
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

    # ================== MEDIA GROUP (PHOTOS) ==================
    group = await get_media_group(context.application.db, key)
    if not group:
        await update.message.reply_text("❌ فایل موردنظر پیدا نشد")
        return

    file_ids = group["file_ids"]

    media = []
    for i, fid in enumerate(file_ids):
        media.append(
            InputMediaPhoto(
                media=fid,
                caption=group["deep_link"] if i == 0 else None
            )
        )

    await bot.send_media_group(
        chat_id=update.effective_chat.id,
        media=media
    )
