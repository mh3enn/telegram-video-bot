import random
import subprocess
from telegram import InputMediaPhoto
import os

async def generate_and_send_demo(bot, video_file_path, deep_link, chat_id, num_frames=10):
    try:
        # ابتدا طول ویدئو را با ffprobe بخوانیم
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_file_path],
            capture_output=True,
            text=True
        )
        duration = float(result.stdout.strip())
        snippet_duration = min(30, duration)  # فقط 30 ثانیه اول اگر طولانی‌تر باشه

        # انتخاب زمان فریم‌ها
        frame_times = [0, snippet_duration/2, snippet_duration-0.1]  # 3 فریم قطعی
        while len(frame_times) < num_frames:
            frame_times.append(random.uniform(0, snippet_duration))
        frame_times = sorted(frame_times[:num_frames])

        media = []
        for idx, t in enumerate(frame_times):
            tmp_file = f"thumb_{idx+1}.jpg"
            # استخراج فریم با ffmpeg
            subprocess.run([
                "ffmpeg", "-ss", str(t), "-i", video_file_path,
                "-frames:v", "1", "-q:v", "2", tmp_file
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            media.append(
                InputMediaPhoto(
                    media=open(tmp_file, "rb"),
                    caption=deep_link if idx == 0 else None
                )
            )

        if media:
            await bot.send_media_group(chat_id=chat_id, media=media)

        # پاک کردن فایل‌های موقت
        for m in media:
            m.media.close()
            os.remove(m.media.name)

    except Exception as e:
        print("❌ Demo generation error:", e)
