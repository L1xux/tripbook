"""이미지 리사이즈+EXIF 촬영일 추출+파일 경로 규칙. / photos 라우터와 analysis가 호출. / Pillow 사용."""
import os
from datetime import datetime
from pathlib import Path
import io
from PIL import Image, ExifTags

MAX_EDGE = 1100  # 왜 1100px: Haiku 비전 분석에 충분하면서 이미지 토큰(≈장당 3원)을 최소화


def small_path(original_path: str) -> str:
    """원본 경로 → 분석용 리사이즈본 경로. 저장(photos 라우터)과 소비(analysis)가 이 규칙 하나를 공유한다."""
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
