import asyncio
import cv2
from tempfile import TemporaryDirectory
from pathlib import Path
from io import BytesIO

from telegram import InputMediaPhoto


async def generate_and_send_demo(
    bot,
    file_id: str,
    deep_link: str,
    chat_id: int,
    frame_count: int = 5,
):
    try:
        with TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"

            tg_file = await bot.get_file(file_id)
            await tg_file.download_to_drive(custom_path=str(video_path))

            images = await _extract_frames(video_path, deep_link, frame_count)

            if images:
                await bot.send_media_group(chat_id=chat_id, media=images)

    except Exception as e:
        print("❌ Demo generation error:", e)


async def _extract_frames(video_path: Path, deep_link: str, frame_count: int):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _sync_extract_frames,
        video_path,
        deep_link,
        frame_count
    )


def _sync_extract_frames(video_path: Path, deep_link: str, frame_count: int):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(total_frames // (frame_count + 1), 1)

    media = []
    current = step
    index = 0

    while index < frame_count and cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, current)
        ret, frame = cap.read()
        if not ret:
            break

        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            current += step
            continue

        bio = BytesIO(buffer.tobytes())
        bio.name = f"demo_{index+1}.jpg"
        bio.seek(0)

        media.append(
            InputMediaPhoto(
                media=bio,
                caption=deep_link if index == 0 else None
            )
        )

        index += 1
        current += step

    cap.release()
    return media
