import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from db import get_video_record, log_download
from utils import build_join_keyboard, build_missing_text, delete_after_delay
from handlers.start import check_user_membership
from cache import clear_cached_membership


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()

    bot = context.bot
    user_id = q.from_user.id
    data = q.data

    if data.startswith("no_link:"):
        _, ch, _ = data.split(":", 2)
        await q.edit_message_text(
            f"❌ لینک عضویت برای کانال {ch} موجود نیست."
        )
        return

    if not data.startswith("check_join:"):
        return

    key = data.split(":", 1)[1]

    clear_cached_membership(user_id)
    missing = await check_user_membership(bot, user_id, use_cache=False)

    if missing:
        kb = await build_join_keyboard(bot, missing, key)
        text = build_missing_text(len(missing))
        await q.edit_message_text(text=text, reply_markup=kb)
        return

    # فایل را از دیتابیس بگیر
    row = await get_video_record(context.application.db, key)
    if not row:
        await q.edit_message_text("❌ فایل پیدا نشد")
        return

    await q.edit_message_text("✅ عضویت تأیید شد، در حال ارسال فایل...")

    msg = await bot.send_video(
        chat_id=user_id,
        video=row["file_id"],
        caption=(
            "📥 این فایل را در Saved Messages ذخیره کنید\n"
            "⏱ فایل بعد از ۳۰ ثانیه حذف می‌شود\n\n"
            "@Fansonly_TG"
        )
    )

    await log_download(context.application.db, key, user_id)

    # حذف بعد از 30 ثانیه
    asyncio.create_task(delete_after_delay(bot, user_id, msg.message_id))
