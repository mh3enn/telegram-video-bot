import asyncio
from tempfile import TemporaryDirectory
from pathlib import Path
from io import BytesIO

import cv2
from moviepy.editor import VideoFileClip
from telegram import InputMediaPhoto


async def generate_and_send_demo(
    bot,
    file_id: str,
    deep_link: str,
    chat_id: int,
    frame_count: int = 5,
):
    """
    دانلود موقت ویدیو، ساخت دمو (چند عکس) و ارسال آن
    بدون ذخیره دائمی روی سرور
    """

    try:
        # ساخت فولدر موقت
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            video_path = tmpdir / "video.mp4"

            # دانلود ویدیو به صورت موقت
            tg_file = await bot.get_file(file_id)
            await tg_file.download_to_drive(custom_path=str(video_path))

            # استخراج فریم‌ها
            images = await _extract_frames(video_path, deep_link, frame_count)

            if images:
                await bot.send_media_group(
                    chat_id=chat_id,
                    media=images
                )

    except Exception as e:
        # مهم: خطای دمو نباید ربات را متوقف کند
        print("❌ Demo generation error:", e)


async def _extract_frames(video_path: Path, deep_link: str, frame_count: int):
    """
    استخراج frame_count فریم از ویدیو و تبدیل به InputMediaPhoto
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _sync_extract_frames,
        video_path,
        deep_link,
        frame_count
    )


def _sync_extract_frames(video_path: Path, deep_link: str, frame_count: int):
    """
    نسخه sync (CPU-bound) برای اجرا داخل ThreadPool
    """
    clip = VideoFileClip(str(video_path))
    duration = clip.duration

    times = [
        duration * i / (frame_count + 1)
        for i in range(1, frame_count + 1)
    ]

    media = []

    for index, t in enumerate(times):
        frame = clip.get_frame(t)  # numpy array (RGB)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        success, buffer = cv2.imencode(".jpg", frame_bgr)
        if not success:
            continue

        bio = BytesIO(buffer.tobytes())
        bio.name = f"demo_{index + 1}.jpg"
        bio.seek(0)

        media.append(
            InputMediaPhoto(
                media=bio,
                caption=deep_link if index == 0 else None
            )
        )

    clip.reader.close()
    if clip.audio:
        clip.audio.reader.close_proc()

    return media