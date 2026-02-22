import traceback
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)
from telegram.ext import filters as tg_filters

from config import TOKEN, ADMIN_GROUP_ID, DATABASE_URL
from db import init_db
from handlers.start import start
from handlers.admin import handle_admin_group_media, stats,handle_media_group
from handlers.callbacks import check_join_callback
from handlers.admin_backup import backup_command, restore_command,handle_restore_file


async def on_startup(app):
    await init_db(app, DATABASE_URL)


async def error_handler(update, context):
    print("❌ Exception occurred:")
    traceback.print_exception(
        type(context.error),
        context.error,
        context.error.__traceback__
    )


def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(CommandHandler("restore", restore_command))
    app.add_handler(
    MessageHandler(
        tg_filters.Chat(ADMIN_GROUP_ID) &
        (tg_filters.VIDEO | tg_filters.Document.VIDEO),
        handle_admin_group_media
       )
    )

    app.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^(check_join:|no_link:)"
        )
    )
    # هندلر مدیا گروپ (عکس)
    app.add_handler(
        MessageHandler(
            tg_filters.Chat(ADMIN_GROUP_ID) & tg_filters.PHOTO,
            handle_media_group
        )
    )
    # هندلر ریستور (فقط فایل JSON در چت ادمین)
    app.add_handler(
        MessageHandler(
            tg_filters.Chat(ADMIN_GROUP_ID) &
            tg_filters.Document.FileExtension("json"),
            handle_restore_file
        )
    )
    app.add_error_handler(error_handler)

    app.run_polling()


if __name__ == "__main__":
    main()


