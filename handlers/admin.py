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

    # اگر اولین عکس آلبومه، تایمر پردازش رو فعال کن
    if gid not in MEDIA_BUFFER:
        MEDIA_BUFFER[gid] = []
        asyncio.create_task(process_media_group(gid, context))

    # ذخیره file_id واقعی (بالاترین کیفیت عکس)
    file_id = msg.photo[-1].file_id
    MEDIA_BUFFER[gid].append(file_id)


async def process_media_group(gid, context):
    # صبر کوتاه برای کامل شدن آلبوم
    await asyncio.sleep(1.2)

    file_ids = MEDIA_BUFFER.pop(gid, [])
    if not file_ids:
        return

    bot = context.bot
    chat_id = ADMIN_GROUP_ID

    me = await bot.get_me()
    deep_link = f"https://t.me/{me.username}?start={gid}"

    # ذخیره file_id های واقعی در دیتابیس
    await save_media_group(
        context.application.db,
        gid,
        file_ids,
        deep_link
    )

    # ساخت آلبوم واقعی با send_media_group
    media = [
        InputMediaPhoto(
            media=fid,
            caption=f"🔗 لینک دریافت:\n{deep_link}" if i == 0 else None
        )
        for i, fid in enumerate(file_ids)
    ]

    sent_messages = await bot.send_media_group(
        chat_id=chat_id,
        media=media
    )

    # اگر خواستی داخل گروه حذف نشه اینو کامنت کن
    #for m in sent_messages:
     #   asyncio.create_task(
          #  delete_after_delay(bot, chat_id, m.message_id)
     #    )
