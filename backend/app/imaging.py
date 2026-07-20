"""이미지 리사이즈+EXIF 촬영일 추출. / photos 라우터가 호출. / Pillow 사용."""
from datetime import datetime
from pathlib import Path
import io
from PIL import Image, ExifTags

MAX_EDGE = 1100  # 왜 1100px: Haiku 비전 분석에 충분하면서 이미지 토큰(≈장당 3원)을 최소화

_DT_TAG = next(k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal")


def save_resized(data: bytes, dest: Path) -> datetime | None:
    img = Image.open(io.BytesIO(data))
    taken_at = None
    try:
        raw = (img._getexif() or {}).get(_DT_TAG)
        if raw:
            taken_at = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(dest, "JPEG", quality=88)
    return taken_at
