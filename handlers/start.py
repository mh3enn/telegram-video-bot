import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes

from db import get_video_record, log_download, get_media_group
from cache import get_cached_membership, set_cached_membership
from utils import build_join_keyboard, build_missing_text, delete_after_delay
from config import SPONSOR_CHANNELS


async def check_user_membership(bot, user_id, use_cache=True):
    """بررسی عضویت کاربر در کانال‌های اسپانسر"""
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
    """هندلر استارت با چک عضویت و ارسال فایل‌ها"""
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
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # ================== ۱. چک عضویت ==================
    missing = await check_user_membership(bot, user_id)
    if missing:
        kb = await build_join_keyboard(bot, missing, key)
        text = build_missing_text(len(missing))
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb
        )
        return

    # ================== ۲. ارسال ویدیو ==================
    row = await get_video_record(context.application.db, key)
    if row:
        msg = await bot.send_video(
            chat_id=chat_id,
            video=row["file_id"],
            caption=(
                "📥 این فایل را در Saved Messages ذخیره کنید\n"
                "⏱ فایل بعد از ۳۰ ثانیه حذف می‌شود\n\n"
                "@Fansonly_TG"
            )
        )

        # لاگ دانلود
        await log_download(context.application.db, key, user_id)

        # حذف بعد از ۳۰ ثانیه
        asyncio.create_task(
            delete_after_delay(bot, chat_id, msg.message_id)
        )
        return

    # ================== ۳. ارسال گروه عکس (Media Group) ==================
    group = await get_media_group(context.application.db, key)
    if not group or not group["file_ids"]:
        await update.message.reply_text("❌ فایل موردنظر پیدا نشد")
        return

    file_ids = group["file_ids"]
    deep_link = group.get("deep_link")

    media = [
    InputMediaPhoto(
        media=fid,
        caption=(
            "📥 این دمو را در Saved Messages ذخیره کنید\n"
            "⏱ دمو بعد از ۳۰ ثانیه حذف می‌شود\n\n"
            "@Fansonly_TG"
            ) if i == 0 else None
        )
        for i, fid in enumerate(file_ids)
    ]


    messages = await bot.send_media_group(
        chat_id=chat_id,
        media=media
    )
    for m in messages:
        asyncio.create_task(
            delete_after_delay(bot, chat_id, m.message_id)
    )
