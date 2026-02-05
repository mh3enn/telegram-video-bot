import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_TITLES, CHANNEL_INVITES, SPONSOR_CHANNELS

def build_missing_text(count: int) -> str:
    if count == 1:
        return "❌ هنوز جوین 1 کانال نشدی\n👇 لطفاً برای دریافت فیلم جوین کانال بشید"
    return f"❌ هنوز جوین {count} کانال نشدی\n👇 لطفاً برای دریافت فیلم جوین کانال‌ها بشید"

async def get_channel_join_link(bot, channel):
    if str(channel) in CHANNEL_INVITES and CHANNEL_INVITES[str(channel)]:
        return CHANNEL_INVITES[str(channel)]

    try:
        chat = await bot.get_chat(chat_id=channel)
        if chat.username:
            return f"https://t.me/{chat.username}"
    except Exception:
        pass

    try:
        invite = await bot.create_chat_invite_link(chat_id=channel)
        return invite.invite_link
    except Exception:
        return None

async def build_join_keyboard(bot, missing_channels, key):
    buttons = []

    for ch in missing_channels:
        link = await get_channel_join_link(bot, ch)
        label = CHANNEL_TITLES.get(ch, "📢 عضویت در کانال اسپانسر")

        if link:
            buttons.append([InlineKeyboardButton(label, url=link)])
        else:
            buttons.append([
                InlineKeyboardButton(
                    f"لینک موجود نیست ({ch})",
                    callback_data=f"no_link:{ch}:{key}"
                )
            ])

    buttons.append([
        InlineKeyboardButton(
            "🔄 بررسی مجدد عضویت",
            callback_data=f"check_join:{key}"
        )
    ])

    return InlineKeyboardMarkup(buttons)
async def delete_after_delay(bot, chat_id, message_id, delay=30):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass
