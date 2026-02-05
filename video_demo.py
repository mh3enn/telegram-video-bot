import os
import random
from tempfile import NamedTemporaryFile
from telegram import InputMediaPhoto
from moviepy import VideoFileClip

async def generate_and_send_demo(bot, video_file_path, deep_link, chat_id, num_frames=10):
    """
    Generate small JPG frames from video and send them via Telegram.
    Safe for large videos and small servers (1GB RAM).
    """
    try:
        clip = VideoFileClip(video_file_path)

        # زمان‌های انتخاب فریم: اول، وسط، آخر + رندوم تا num_frames
        times = [0, clip.duration / 2, max(clip.duration - 1, 0)]
        if num_frames > len(times):
            remaining = num_frames - len(times)
            random_times = sorted(random.sample(range(int(clip.duration)), remaining))
            times.extend(random_times)
        times = sorted(times)[:num_frames]

        media = []
        for idx, t in enumerate(times):
            with NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            # ذخیره فریم با کیفیت پایین برای کاهش حجم
            clip.save_frame(tmp_path, t)

            # کاهش حجم با re-save با کیفیت کمتر (اختیاری)
            from PIL import Image
            img = Image.open(tmp_path)
            img.save(tmp_path, format="JPEG", quality=50)  # کیفیت JPG کم میشه
            img.close()

            media.append(
                InputMediaPhoto(
                    media=open(tmp_path, "rb"),
                    caption=deep_link if idx == 0 else None
                )
            )

        if media:
            await bot.send_media_group(chat_id=chat_id, media=media)

        # پاک کردن temp فریم‌ها
        for m in media:
            m.media.close()
            os.remove(m.media.name)

        clip.close()

    except Exception as e:
        print("❌ Demo generation error:", e)
