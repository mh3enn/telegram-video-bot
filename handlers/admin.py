import asyncio
from telegram import Update,InputMediaPhoto
from telegram.ext import ContextTypes

from config import ADMIN_GROUP_ID
from db import (
    get_total_videos,
    get_total_downloads,
    get_today_downloads,
    save_video_record,
    save_media_group,
)

async def handle_admin_group_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != ADMIN_GROUP_ID:
        return

    if not (msg.video or msg.document):
        return

    # فقط ادمین‌ها
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
    bot_username = context.bot.username or (await context.bot.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start={key}"

    # ذخیره در دیتابیس
    await save_video_record(
        context.application.db,
        message_id=key,
        file_id=file_id,
        title=title,
        caption=caption,
        deep_link=deep_link
    )

    # ✅ ارسال مجدد خود ویدیو
    await context.bot.send_video(
        chat_id=ADMIN_GROUP_ID,
        video=file_id,
        caption=f"🎬 {title}\n\n🔗 لینک دریافت:\n{deep_link}"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_videos = await get_total_videos(context.application.db)
    total_downloads = await get_total_downloads(context.application.db)
    today_downloads = await get_today_downloads(context.application.db)

    text = (
        "📊 Bot Stats\n\n"
        f"🎬 Total videos: {total_videos}\n"
        f"⬇️ Total downloads: {total_downloads}\n"
        f"📅 Today downloads: {today_downloads}"
    )

    await update.message.reply_text(text)


async def handle_media_group(update, context):
    msg = update.message
    if  not msg or not msg.media_group_id:
        return

    bot = context.bot
    chat_id = msg.chat.id
    media_group_id = msg.media_group_id
    photos = msg.photo  # list of PhotoSize

    if len(photos) != 10:
        return  # فقط واکنش به گروه ۱۰ عکس

    # واکنش به پیام
    await msg.reply_text("👍 10 عکس دریافت شد!")

    # ساخت دیپ لینک
    me = await bot.get_me()
    deep_link = f"https://t.me/{me.username}?start={media_group_id}"

    # ذخیره file_idها
    file_ids = [p.file_id for p in photos]
    await save_media_group(context.application.db, media_group_id, file_ids, deep_link)

    # ارسال media group همراه دیپ لینک
    media = [
        InputMediaPhoto(
            file_id=f,
            caption=deep_link if i == 0 else None  # فقط اولین عکس کپشن دارد
        )
        for i, f in enumerate(file_ids)
    ]
    await bot.send_media_group(chat_id=chat_id, media=media)
