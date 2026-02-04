import asyncio
from telegram import Update
from telegram.ext import ContextTypes

from db import get_video_record, log_download
from utils import build_join_keyboard, build_missing_text
from handlers.start import check_user_membership


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
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

    missing = await check_user_membership(bot, user_id)

    if missing:
        kb = await build_join_keyboard(bot, missing, key)
        text = build_missing_text(len(missing))
        await q.edit_message_text(text=text, reply_markup=kb)
        return

    row = await get_video_record(context.application.db, key)
    if not row:
        await q.edit_message_text("❌ فایل پیدا نشد")
        return

    await q.edit_message_text("✅ عضویت تأیید شد، در حال ارسال فایل...")

    msg = await bot.send_video(
        chat_id=user_id,
        video=row["file_id"],
        caption="📥 فایل ارسال شد"
    )

    await log_download(context.application.db, key, user_id)

    asyncio.create_task(
        delete_after_delay(bot, user_id, msg.message_id)
  )
