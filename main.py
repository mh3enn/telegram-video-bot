import os
import json
import asyncio
import asyncpg
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.ext import filters as tg_filters
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")

# —————— پیکربندی کانال‌های اسپانسر ——————
#username ("@mychannel") برای کانال پابلیک
# chat_id (-1001234567890) برای کانال خصوصی 
SPONSOR_CHANNELS = [
    "@fansonly90775",
    "@FansonlyBackup"
]
CHANNEL_TITLES = {
    "@fansonly90775": "📢 عضویت در کانال اصلی",
  "@FansonlyBackup": "📢 عضویت در کانال پشتیبان"
}
#روش پیاده سازی در چنل اینوایت 
#مقدار none لینک عضویت و دعوت هست
# "-1001234567890": "https://t.me/joinchat/AAAAAExampleInvite",
    # "@PublicChannelName": None 
CHANNEL_INVITES = {}
# =======================
# دیتابیس: schema + helpers
# =======================
DB_TABLE = "videos"

async def init_db_schema(pool):
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {DB_TABLE} (
                id SERIAL PRIMARY KEY,
                message_id TEXT UNIQUE,
                file_id TEXT NOT NULL,
                title TEXT,
                caption TEXT,
                deep_link TEXT,
                thumbnail_file_id TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

async def save_video_record(pool, message_id, file_id, title, caption, deep_link, thumbnail_file_id=None):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"""
            INSERT INTO {DB_TABLE} (message_id, file_id, title, caption, deep_link, thumbnail_file_id, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (message_id) DO UPDATE
            SET file_id = EXCLUDED.file_id,
                title = EXCLUDED.title,
                caption = EXCLUDED.caption,
                deep_link = EXCLUDED.deep_link,
                thumbnail_file_id = EXCLUDED.thumbnail_file_id,
                created_at = EXCLUDED.created_at
            RETURNING id, message_id;
        """, str(message_id), file_id, title, caption, deep_link, thumbnail_file_id, datetime.now(ZoneInfo("Asia/Tehran")))
        return row  # row['id'], row['message_id']

async def get_video_record(pool, message_id):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {DB_TABLE} WHERE message_id = $1", str(message_id))
        return row

# ================================
# ذخیره file_id بر اساس لینک پست کانال
# ================================
def build_missing_text(missing_count):
    if missing_count == 1:
        return "❌ هنوز جوین 1 از کانال های زیر نشدی\n👇 لطفاً برای دریافت فیلم جوین کانال های زیر بشید"
    else:
        return f"❌ هنوز جوین {missing_count} کانال زیر نشدی\n👇 لطفاً برای دریافت فیلم جوین کانال های زیر بشید"
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
    key = f"{msg.chat.id}:{msg.message_id}"
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
    # ایجاد connection pool
    application.db = await asyncpg.create_pool(DATABASE_URL)
    # ساخت schema (اگر لازم بود)
    await init_db_schema(application.db)
    print("DB pool created and schema ensured")

# ================================
# مدیریت /start با پارامتر لینک
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لینک دریافت فایل نامعتبر است.")
        return

    key = context.args[0]
    # جدول DB را بخوان
    row = await get_video_record(context.application.db, key)
    if not row:
        await update.message.reply_text("❌ فایل پیدا نشد")
        return

    user_id = update.effective_user.id
    bot = context.bot
    missing = await check_user_membership(bot, user_id)

    if not missing:
        msg = await bot.send_video(
            chat_id=update.effective_chat.id,
            video=row['file_id'],
            caption="📥 این فایل توی Saved Messages ذخیره کن\n⏱ این فایل بعد از ۳۰ ثانیه حذف میشه"
        )
        asyncio.create_task(delete_after_delay(bot, update.effective_chat.id, msg.message_id, 30))
        return

    kb = await build_join_keyboard(bot, missing, key)
    text = build_missing_text(len(missing))
    await bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=kb)


# —————— تابع کمکی: بررسی عضویت کاربر در کانال‌ها ——————
async def check_user_membership(bot, user_id):
    """
    برمی‌گرداند: لیست channel_ids که کاربر هنوز عضو آنها نیست.
    """
    missing = []
    for ch in SPONSOR_CHANNELS:
        try:
            # get_chat_member ممکن است Exception بدهد اگر ربات عضو کانال نباشد یا دسترسی نداشته باشد
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            status = member.status  # "member", "administrator", "left", ...
            if status not in ("member", "administrator", "creator"):
                missing.append(ch)
        except Exception as e:
            # اگر نتوانیم وضعیت را چک کنیم، فرض می‌کنیم عضو نیستند (و لاگ می‌زنیم)
            print(f"⚠️ خطا در get_chat_member برای {ch}: {e}")
            missing.append(ch)
    return missing

# —————— تابع کمکی: گرفتن لینک عضویت (یا ساختن آن) ——————
async def get_channel_join_link(bot, channel):
   
    if str(channel) in CHANNEL_INVITES and CHANNEL_INVITES[str(channel)]:
        return CHANNEL_INVITES[str(channel)]

    try:
        chat = await bot.get_chat(chat_id=channel)
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}"
    except Exception as e:
        # ممکن است برای چنل خصوصی این خطا بیاید؛ سپس سعی می‌کنیم invite بسازیم
        print(f"info: couldn't get chat username for {channel}: {e}")

    try:
        invite = await bot.create_chat_invite_link(chat_id=channel)
        return invite.invite_link
    except Exception as e:
        print(f"⚠️ couldn't create invite link for {channel}: {e}")
        return None

# —————— تابع کمکی: ساخت کیبورد join + دکمه Validate ——————
async def build_join_keyboard(bot, missing_channels, key):
    """
    ساخت inline keyboard:
    - برای هر کانال missing یک دکمه URL برای عضویت تولید می‌کند
    - در آخر یک دکمه callback برای "من عضو شدم" با callback_data = "check_join:<key>"
    """
    buttons = []
    for ch in missing_channels:
        link = await get_channel_join_link(bot, ch)
        label = CHANNEL_TITLES.get(ch, "📢 عضویت در کانال اسپانسر")
        if link:
            buttons.append([InlineKeyboardButton(label, url=link)])
        else:
            # اگر لینک نداریم، دکمه‌ای بساز که کاربر را راهنمایی کند (بدون URL)
            buttons.append([InlineKeyboardButton(f"لینک موجود نیست برای {str(ch)}", callback_data=f"no_link:{ch}:{key}")])

    # دکمه "من عضو شدم" (صحت سنجی)
    buttons.append([InlineKeyboardButton("✅ من عضو شدم", callback_data=f"check_join:{key}")])

    return InlineKeyboardMarkup(buttons)
    
# —————— Callback handler برای دکمه "من عضو شدم" و پیغام‌های مرتبط ——————
async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data_cb = q.data
    bot = context.bot
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

    # همه کانال‌ها جوین شده‌اند
    try:
        await q.delete_message()
    except:
        pass

    # خواندن ویدیو از دیتابیس
    row = await get_video_record(context.application.db, key)
    if not row:
        await bot.send_message(
            chat_id=user_id,
            text="❌ متأسفانه فایل پیدا نشد."
        )
        return

    msg = await bot.send_video(
        chat_id=user_id,
        video=row["file_id"],
        caption="📥 این فایل را در Saved Messages ذخیره کنید\n⏱ این فایل بعد از ۳۰ ثانیه حذف می‌شود"
    )

    asyncio.create_task(
        delete_after_delay(bot, user_id, msg.message_id, 30)
    )
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
app.add_handler(MessageHandler(tg_filters.Chat(ADMIN_GROUP_ID) & (tg_filters.VIDEO | tg_filters.Document.ALL), handle_admin_group_media))
app.add_handler(CallbackQueryHandler(check_join_callback, pattern=r"^(check_join:|no_link:)"))
# ================================
# اجرای مانیتورینگ فایل با asyncio
# ================================
if __name__ == "__main__":
    # اجرای مانیتورینگ در یک task جدید
    app.run_polling()


