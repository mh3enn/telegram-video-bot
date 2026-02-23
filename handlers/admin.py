import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes
from collections import defaultdict

from config import ADMIN_GROUP_ID
from utils import collect_media_group, delete_after_delay
from db import (
    get_total_videos,
    get_total_downloads,
    get_today_downloads,
    save_video_record,
    save_media_group,
)

# ======================= ویدیوهای ادمین =======================
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
    caption = msg.caption or ""
    title = caption.splitlines()[0] if caption else "بدون عنوان"

    # کلید اصلی برای ذخیره و ارسال
    key = f"{msg.chat.id}_{msg.message_id}"
    bot_username = context.bot.username or (await context.bot.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start={key}"

    # ذخیره در دیتابیس
    await save_video_record(
        context.application.db,
        message_id=key,
        file_id=media.file_id,  # هنوز برای هماهنگی با DB
        title=title,
        caption=caption,
        deep_link=deep_link
    )

    # ✅ ارسال مجدد با copy_message (ضد بن)
    msg_sent = await context.bot.copy_message(
        chat_id=ADMIN_GROUP_ID,
        from_chat_id=msg.chat.id,
        message_id=msg.message_id,
        caption=f"🎬 {title}\n\n🔗 لینک دریافت:\n{deep_link}"
    )

    # حذف بعد از ۳۰ ثانیه
    # asyncio.create_task(delete_after_delay(context.bot, ADMIN_GROUP_ID, msg_sent.message_id))


# ======================= آمار =======================
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


# ======================= مدیا گروپ =======================
MEDIA_BUFFER = {}

async def handle_media_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.media_group_id or not msg.photo:
        return

    gid = msg.media_group_id
    key = f"{msg.chat.id}_{msg.message_id}"  # کلید برای هر عکس

    if gid not in MEDIA_BUFFER:
        MEDIA_BUFFER[gid] = []

    MEDIA_BUFFER[gid].append(key)

    # هنوز کامل نشده
    if len(MEDIA_BUFFER[gid]) < 10:
        return

    # دقیقاً ۱۰ عکس
    keys = MEDIA_BUFFER.pop(gid)

    bot = context.bot
    me = await bot.get_me()
    deep_link = f"https://t.me/{me.username}?start={gid}"

    # ذخیره در دیتابیس (کلیدها)
    await save_media_group(
        context.application.db,
        gid,
        keys,
        deep_link
    )

    # ارسال با copy_message برای هر عکس
    messages = []
    for i, key in enumerate(keys):
        source_chat_id, source_message_id = key.split("_")
        msg_sent = await bot.copy_message(
            chat_id=msg.chat.id,
            from_chat_id=int(source_chat_id),
            message_id=int(source_message_id),
            caption=deep_link if i == 0 else None
        )
        messages.append(msg_sent)

    # حذف بعد از ۳۰ ثانیه
    for m in messages:
        asyncio.create_task(delete_after_delay(bot, msg.chat.id, m.message_id))
