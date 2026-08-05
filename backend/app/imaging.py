"""이미지 리사이즈와 촬영일 추출, 파일 경로 규칙. / photos 라우터와 analysis가 호출. / Pillow 사용."""
import os
from datetime import datetime
from pathlib import Path
import io
from PIL import Image, ExifTags

MAX_EDGE = 1100  # 비전 분석에 충분하면서 이미지 토큰을 아끼는 크기


def small_path(original_path: str) -> str:
    """원본 경로에서 분석용 리사이즈본 경로를 만든다. 저장하는 쪽과 쓰는 쪽이 이 규칙을 공유한다."""
    small = original_path.replace(".jpg", "_small.jpg")
    return small if os.path.exists(small) else original_path


def save_resized(data: bytes, dest: Path) -> datetime | None:
    img = Image.open(io.BytesIO(data))
    taken_at = None
    try:
        raw = (img._getexif() or {}).get(ExifTags.Base.DateTimeOriginal)
        if raw:
            taken_at = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(dest, "JPEG", quality=88)
    return taken_at
