import os
import random
from tempfile import NamedTemporaryFile
from telegram import InputMediaPhoto

from moviepy.editor import VideoFileClip  # اصلاح import

async def generate_and_send_demo(bot, video_file_path, deep_link, chat_id, max_size_mb=50, num_frames=10):
    try:
        # بارگذاری ویدیو اصلی
        clip = VideoFileClip(video_file_path)
        
        # کوتاه کردن ویدیو به 1 دقیقه برای demo (~50MB)
        if clip.duration > 60:
            clip = clip.subclip(0, 60)

        # انتخاب فریم‌ها بصورت تصادفی
        frame_times = sorted(random.sample(range(int(clip.duration)), min(num_frames, int(clip.duration))))
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

        # ارسال گروهی فریم‌ها
        if media:
            await bot.send_media_group(chat_id=chat_id, media=media)

        # پاک کردن temp فریم‌ها
        for m in media:
            m.media.close()
            os.remove(m.media.name)

        clip.close()
    except Exception as e:
        print("❌ Demo generation error:", e)
