import os
import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "files.json"

# ایجاد فایل ذخیره‌سازی اگر وجود نداشته باشد
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

with open(DB_FILE, "r") as f:
    data = json.load(f)
print("داده‌های اولیه:", data)
async def post_init(application):
    application.create_task(monitor_json_file())
# ================================
# ذخیره file_id بر اساس لینک پست کانال
# ================================

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

# حذف پیام بعد ۳۰ ثانیه
async def delete_after_delay(bot, chat_id, message_id, delay=30):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# ================================
# مدیریت /start با پارامتر لینک
# ===============================
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

    msg = await context.bot.send_video(
    chat_id=update.effective_chat.id,
    video=data[key],
    caption="📥 این فایل توی Saved Messages ذخیره کن\n⏱ این فایل بعد از ۳۰ ثانیه حذف میشه"
)

    asyncio.create_task(  # تغییر این قسمت
        delete_after_delay(
            context.bot,
            update.effective_chat.id,
            msg.message_id,
            30
        )
    )

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

# ================================
# ساخت اپلیکیشن و هندلرها
# ================================
app = (
    ApplicationBuilder()
    .token(TOKEN)
    .post_init(post_init)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_file))

# ================================
# اجرای مانیتورینگ فایل با asyncio
# ================================
if __name__ == "__main__":
    # اجرای مانیتورینگ در یک task جدید
    app.run_polling()


