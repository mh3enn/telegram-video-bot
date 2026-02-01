import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "files.json"


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
# ایجاد فایل ذخیره‌سازی اگر وجود نداشته باشد
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

with open(DB_FILE, "r") as f:
    data = json.load(f)
print("داده‌های اولیه:", data)
# ================================
# ذخیره file_id بر اساس لینک پست کانال
# ================================
def build_missing_text(missing_count):
    if missing_count == 1:
        return "❌ هنوز جوین 1 از کانال های زیر نشدی\n👇 لطفاً برای دریافت فیلم جوین کانال های زیر بشید"
    else:
        return f"❌ هنوز جوین {missing_count} کانال زیر نشدی\n👇 لطفاً برای دریافت فیلم جوین کانال های زیر بشید"
"""       تابع ذخیره فایل
def save_file_id(post_link, file_id):
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    data[post_link] = file_id
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ================================
# دریافت فایل از کانال و ذخیره file_id
# ================================
async def handle_channel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post or not post.video:
        return

    file_id = post.video.file_id
    message_id = post.message_id  # 👈 این خط حیاتی بود

    with open(DB_FILE, "r") as f:
        data = json.load(f)

    data[str(message_id)] = file_id

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

    deep_link = f"https://t.me/Uploader11113221_bot?start={message_id}"
    print("✅ لینک دریافت فایل:", deep_link)
"""
# حذف پیام بعد ۳۰ ثانیه
async def delete_after_delay(bot, chat_id, message_id, delay=30):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# ================================
# مدیریت /start با پارامتر لینک
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لینک دریافت فایل نامعتبر است.")
        return

    key = context.args[0]

    with open(DB_FILE, "r") as f:
        data = json.load(f)

    if key not in data:
        await update.message.reply_text("❌ فایل پیدا نشد")
        return

    user_id = update.effective_user.id
    bot = context.bot

    # 1) بررسی عضویت در کانال‌های اسپانسر
    missing = await check_user_membership(bot, user_id)

    if not missing:
        # همه عضو هستند -> فایل عادی ارسال می‌شود
        msg = await bot.send_video(
            chat_id=update.effective_chat.id,
            video=data[key],
            caption="📥 این فایل توی Saved Messages ذخیره کن\n⏱ این فایل بعد از ۳۰ ثانیه حذف میشه"
        )
        # حذف پس از 30 ثانیه (task پس‌زمینه)
        asyncio.create_task(delete_after_delay(bot, update.effective_chat.id, msg.message_id, 30))
        return

    # 2) کاربر عضو همه کانال‌ها نیست -> نمایش دکمه‌های لینک عضویت
    kb = await build_join_keyboard(bot, missing, key)
    text = build_missing_text(len(missing))

    await bot.send_message(
       chat_id=update.effective_chat.id,
       text=text,
       reply_markup=kb
    )

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
    """
# ================================
# مانیتورینگ تغییر فایل JSON با async
# ================================
async def monitor_json_file():
    last_modified = os.path.getmtime(DB_FILE)
    while True:
        current_modified = os.path.getmtime(DB_FILE)
        if current_modified != last_modified:
            last_modified = current_modified
            with open(DB_FILE, "r") as f:
                data = json.load(f)
            print("فایل JSON تغییر کرد:", data)
        await asyncio.sleep(1)
async def post_init(application):
    application.create_task(monitor_json_file()) """
# —————— Callback handler برای دکمه "من عضو شدم" و پیغام‌های مرتبط ——————
async def check_join_callback(update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()  # پاسخدهی فوری به callback query (بدون متن)

    data_cb = q.data  # مثال: "check_join:45" یا "no_link:-100123:45"
    bot = context.bot
    user_id = q.from_user.id

    if data_cb.startswith("no_link:"):
        # اگر کاربر روی دکمه‌ای که لینک نداشت زد، بهش بگو مدیر کانال باید invite بذاره.
        _, ch, key = data_cb.split(":", 2)
        await q.edit_message_text(f"لینک دعوت برای کانال {ch} موجود نیست. لطفاً به ادمین پیام دهید تا invite ایجاد کند.")
        return

    if not data_cb.startswith("check_join:"):
        await q.answer("عمل نامشخص")
        return

    key = data_cb.split(":", 1)[1]

    # دوباره برداریم که کدام کانال‌ها هنوز missing هستند
    missing = await check_user_membership(bot, user_id)

    if missing:
        # اگر هنوز عضو نشده‌اند، فقط کانال‌های باقی‌مانده را نشان بدهیم
        kb = await build_join_keyboard(bot, missing, key)
        text = build_missing_text(len(missing))
        await q.edit_message_text(
           text=text,
           reply_markup=kb
        )
        return

    # همه عضو شدند — پیام حاوی فایل را ارسال کن و پیام دستور را پاک کن
    # ابتدا پیام دکمه را حذف کن (یا ویرایش)
    try:
        await q.delete_message()
    except Exception:
        pass

    # ارسال فایل
    with open(DB_FILE, "r") as f:
        data_store = json.load(f)

    if key not in data_store:
        # نادر: کلید ناپدید شده
        await bot.send_message(chat_id=user_id, text="متأسفم، فایل دیگر در دسترس نیست.")
        return

    msg = await bot.send_video(
        chat_id=user_id,
        video=data_store[key],
        caption="📥 این فایل توی Saved Messages ذخیره کن\n⏱ این فایل بعد از ۳۰ ثانیه حذف میشه"
    )
    asyncio.create_task(delete_after_delay(bot, user_id, msg.message_id, 30))
# ================================
# ساخت اپلیکیشن و هندلرها
# ================================
app = (
    ApplicationBuilder()
    .token(TOKEN)
    #.post_init(post_init)
    .build()
)

app.add_handler(CommandHandler("start", start))
#app.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_file)) هندلر مربوط به ذخیره از کانال
app.add_handler(CallbackQueryHandler(check_join_callback, pattern=r"^(check_join:|no_link:)"))
# ================================
# اجرای مانیتورینگ فایل با asyncio
# ================================
if __name__ == "__main__":
    # اجرای مانیتورینگ در یک task جدید
    app.run_polling()












