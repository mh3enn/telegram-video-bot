from io import BytesIO
from telegram import InputMediaPhoto


async def send_video_thumbnails(bot, thumbnails, deep_link, chat_id):
    media = []

    for index, thumb in enumerate(thumbnails):
        try:
            tg_file = await bot.get_file(thumb.file_id)
            bio = BytesIO()
            await tg_file.download_to_memory(out=bio)
            bio.seek(0)
            bio.name = f"thumb_{index+1}.jpg"

            media.append(
                InputMediaPhoto(
                    media=bio,
                    caption=deep_link if index == 0 else None
                )
            )
        except Exception as e:
            print("❌ Thumbnail error:", e)

    if media:
        await bot.send_media_group(chat_id=chat_id, media=media)
