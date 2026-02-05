import random
import os
from telegram import InputMediaPhoto
from tempfile import NamedTemporaryFile
from moviepy import VideoFileClip

async def generate_and_send_demo(bot, video_file_path, deep_link, chat_id, num_frames=10, snippet_duration=30):
    try:
        # فقط snippet_duration ثانیه اول ویدیو رو load کن
        clip = VideoFileClip(video_file_path)
        duration = min(clip.duration, snippet_duration)
        clip = clip.subclip(0, duration)

        # انتخاب فریم‌ها بصورت تصادفی در طول snippet
        frame_times = sorted(random.sample(range(int(duration)), min(num_frames, int(duration))))
        media = []

        for idx, t in enumerate(frame_times):
            frame_path = f"thumb_{idx+1}.jpg"
            clip.save_frame(frame_path, t)
            media.append(
                InputMediaPhoto(
                    media=open(frame_path, "rb"),
                    caption=deep_link if idx == 0 else None
                )
            )

        if media:
            await bot.send_media_group(chat_id=chat_id, media=media)

        # پاک کردن فایل‌های temp
        for m in media:
            m.media.close()
            os.remove(m.media.name)

        clip.close()

    except Exception as e:
        print("❌ Demo generation error:", e)
