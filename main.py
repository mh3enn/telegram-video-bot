import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.ext import filters as tg_filters
from db import (
    init_db,
    save_video_record,
    get_video_record,
    log_download,
    get_total_videos,
    get_total_downloads,
    get_today_downloads,
)
from config import (
    TOKEN,
    ADMIN_GROUP_ID,
    DATABASE_URL,
    BOT_ADMIN_ID,
    SPONSOR_CHANNELS,
    CHANNEL_TITLES,
    CHANNEL_INVITES,
)
from cache import get_cached_membership, set_cached_membership
from utils import build_join_keyboard, build_missing_text
def is_admin(user_id: int) -> bool:
    return user_id == BOT_ADMIN_ID

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ دسترسی ندارید")
        return

    pool = context.application.db

    total_videos = await get_total_videos(pool)
    total_downloads = await get_total_downloads(pool)
    today_downloads = await get_today_downloads(pool)

    await update.message.reply_text(
        "📊 آمار ربات\n\n"
        f"🎬 تعداد ویدیوها: {total_videos}\n"
        f"⬇️ کل دانلودها: {total_downloads}\n"
        f"📅 دانلودهای امروز: {today_downloads}"
    )

# ----------------------------------------
# Handler جدید: دریافت فایل از گروه ادمین
# ----------------------------------------
async def handle_admin_group_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    # فقط از گروه مشخص پردازش کن
    if msg.chat.id != ADMIN_GROUP_ID:
        return

    # فقط اگر پیام حاوی ویدیو یا داکیومنت باشه ادامه بده
    media = None
    if msg.video:
        media = msg.video
        media_type = "video"
    elif msg.document:
        media = msg.document
        media_type = "document"
    else:
        return

    # اگر می‌خواهی فقط ادمین‌ها بتوانند ارسال کنند:
    try:
        member = await context.bot.get_chat_member(chat_id=ADMIN_GROUP_ID, user_id=msg.from_user.id)
        if member.status not in ("creator", "administrator"):
            # اگر فرستنده ادمین نیست، نادیده بگیر
            return
    except Exception as e:
        print("Could not check sender admin status:", e)
        # بهتر است در این حالت پیام را نپذیریم تا امنیت حفظ شود
        return

    file_id = media.file_id
    caption = msg.caption or ""
    title = caption.splitlines()[0].strip() if caption else (getattr(media, "file_name", None) or "بدون عنوان")
    thumb_id = None
    try:
        if getattr(media, "thumb", None):
            thumb_id = media.thumb.file_id
    except Exception:
        thumb_id = None

    # شناسهٔ ذخیره (ما از chat_id:message_id استفاده می‌کنیم)
    key = f"{msg.chat.id}_{msg.message_id}"
    bot_username = context.bot.username or (await context.bot.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start={key}"

    # ذخیره در DB
    try:
        row = await save_video_record(context.application.db, message_id=key, file_id=file_id,
                                      title=title, caption=caption, deep_link=deep_link, thumbnail_file_id=thumb_id)
        saved_id = row['id'] if row else key
    except Exception as e:
        print("DB write failed:", e)
        # اگر خواستی می‌تونیم fallback به JSON بذاریم؛ اما پیشنهاد می‌کنم اول DB درست کار کنه
        saved_id = key

    # پست دوبارهٔ ویدئو در گروه برای آرشیو / دسترسی
    try:
        await context.bot.send_video(
            chat_id=ADMIN_GROUP_ID,
            video=file_id,
            caption=f"🎬 {title}\n\n🔗 لینک دریافت: {deep_link}\n\n{caption}"
        )
    except Exception as e:
        print("Failed to re-post video into admin group:", e)
        # fallback: فقط پیام با لینک
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"🎬 {title}\n\n🔗 لینک دریافت: {deep_link}\n\n{caption}")

    print("Saved media:", saved_id, file_id)


# حذف پیام بعد ۳۰ ثانیه
async def delete_after_delay(bot, chat_id, message_id, delay=30):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass
async def on_startup(application):
    await init_db(application, DATABASE_URL)
    print("DB pool & schemas ready")

# ================================
# مدیریت /start با پارامتر لینک
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text( "👋 سلام!\n\n"
            "📥 این ربات برای دریافت ویدیوها استفاده می‌شود.\n"
            "🔗لطفا برای دریافت فیلم عضو کانال زیر بشین\n\n"
            "@Fansonly_TG"
        )
        return

    key = context.args[0]
    # جدول DB را بخوان
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
            video=row['file_id'],
            caption=(
                "📥 این فایل توی Saved Messages ذخیره کن\n"
                "فایل بعد از ۳۰ ثانیه حذف میشه ⏱\n\n"
                "@Fansonly_TG"
            )
            
        )
        await log_download(context.application.db, key, user_id)
        asyncio.create_task(delete_after_delay(bot, update.effective_chat.id, msg.message_id, 30))
        return

    kb = await build_join_keyboard(bot, missing, key)
    text = (
        f"❌ هنوز جوین {len(missing)} کانال نشدي\n"
        "👇 لطفاً برای دریافت فایل در کانال‌های زیر عضو شوید"
     )
    await bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=kb
    )
async def check_user_membership(bot, user_id):
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

    set_cached_membership(user_id, missing)
    return missing
    
# —————— Callback handler برای دکمه "من عضو شدم" و پیغام‌های مرتبط ——————
async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bot = context.bot
    data_cb = q.data
    user_id = q.from_user.id

    if data_cb.startswith("no_link:"):
        _, ch, _ = data_cb.split(":", 2)
        await q.edit_message_text(
            f"❌ لینک عضویت برای کانال {ch} موجود نیست.\n"
            "لطفاً به ادمین اطلاع دهید."
        )
        return

    if not data_cb.startswith("check_join:"):
        return

    key = data_cb.split(":", 1)[1]

    # بررسی مجدد عضویت
    missing = await check_user_membership(bot, user_id)

    if missing:
        kb = await build_join_keyboard(bot, missing, key)
        text = build_missing_text(len(missing))
        await q.edit_message_text(text=text, reply_markup=kb)
        return
    # خواندن ویدیو از دیتابیس
    row = await get_video_record(context.application.db, key)
    if not row:
        await q.edit_message_text("❌ متأسفانه فایل پیدا نشد.")
        return

    await q.edit_message_text("✅ عضویت شما تأیید شد، فایل در حال ارسال است...")

    msg = await bot.send_video(
        chat_id=user_id,
        video=row["file_id"],
        caption=(
            f"🎬 {row['title'] or ''}\n\n"
            "📥 این فایل را در Saved Messages ذخیره کنید\n"
            "⏱ این فایل بعد از ۳۰ ثانیه حذف می‌شود\n\n"
            "@Fansonly_TG"
        )
    )

    await log_download(context.application.db, key, user_id)

    asyncio.create_task(
        delete_after_delay(bot, user_id, msg.message_id, 30)
    )
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    Error handler سراسری برای کل ربات
    """
    error = context.error

    print("❌ Exception caught:")
    print(error)

    # اگر خطا مربوط به Conflict (چند instance) بود
    if "Conflict" in str(error):
        print("⚠️ Bot conflict detected (multiple instances running)")
        return

    # اگر update وجود داشت و کاربر داشت
    try:
        if update and isinstance(update, Update):
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ خطایی رخ داد. لطفاً چند لحظه بعد دوباره تلاش کنید."
                )
    except Exception:
        # حتی اگر ارسال پیام هم شکست خورد، ربات نباید کرش کند
        pass
# ================================
# ساخت اپلیکیشن و هندلرها
# ================================
app = (
    ApplicationBuilder()
    .token(TOKEN)
    .post_init(on_startup)
    .build()
)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(MessageHandler(tg_filters.Chat(ADMIN_GROUP_ID) & (tg_filters.VIDEO | tg_filters.Document.ALL), handle_admin_group_media))
app.add_handler(CallbackQueryHandler(check_join_callback, pattern=r"^(check_join:|no_link:)"))
app.add_error_handler(error_handler)
# ================================
# اجرای مانیتورینگ فایل با asyncio
# ================================
if __name__ == "__main__":
    # اجرای مانیتورینگ در یک task جدید
    app.run_polling()





