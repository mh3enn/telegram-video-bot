import asyncio
from video_demo import generate_and_send_demo
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_GROUP_ID
from video_demo import generate_and_send_demo
from db import (
    save_video_record,
    get_total_videos,
    get_total_downloads,
    get_today_downloads
)

async def handle_admin_group_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != ADMIN_GROUP_ID:
        return

    if not (msg.video or msg.document):
        return

    try:
        member = await context.bot.get_chat_member(
            chat_id=ADMIN_GROUP_ID,
            user_id=msg.from_user.id
        )
        if member.status not in ("creator", "administrator"):
            return
    except Exception:
        return

    media = msg.video or msg.document
    file_id = media.file_id
    caption = msg.caption or ""
    title = caption.splitlines()[0] if caption else "بدون عنوان"

    key = f"{msg.chat.id}_{msg.message_id}"
    me = await context.bot.get_me()
    bot_username = me.username
    deep_link = f"https://t.me/{bot_username}?start={key}"

    await save_video_record(
        context.application.db,
        message_id=key,
        file_id=file_id,
        title=title,
        caption=caption,
        deep_link=deep_link
    )

    await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=f"🎬 {title}\n\n🔗 لینک دریافت:\n{deep_link}"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.application.db
    total_videos = await get_total_videos(pool)
    total_downloads = await get_total_downloads(pool)
    today_downloads = await get_today_downloads(pool)

    text = (
        f"📊 Bot Stats\n\n"
        f"🎬 Total videos: {total_videos}\n"
        f"⬇️ Total downloads: {total_downloads}\n"
        f"📅 Today downloads: {today_downloads}"
    )
    await update.message.reply_text(text)
