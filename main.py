from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)
from telegram.ext import filters as tg_filters

from config import TOKEN, ADMIN_GROUP_ID,DATABASE_URL
from db import init_db
from handlers.start import start
from handlers.admin import handle_admin_group_media
from handlers.callbacks import check_join_callback


async def on_startup(app):
    await init_db(app, DATABASE_URL)


def error_handler(update, context):
    print(context.error)


app = (
    ApplicationBuilder()
    .token(TOKEN)
    .post_init(on_startup)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(
    MessageHandler(
        tg_filters.Chat(ADMIN_GROUP_ID) &
        (tg_filters.VIDEO | tg_filters.Document.ALL),
        handle_admin_group_media
    )
)
app.add_handler(
    CallbackQueryHandler(check_join_callback, pattern=r"^(check_join:|no_link:)")
)

app.add_error_handler(error_handler)

if __name__ == "__main__":
    app.run_polling()

