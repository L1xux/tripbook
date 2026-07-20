"""사진 비전 분석(Haiku 4.5). / photos 라우터가 백그라운드로 호출. / anthropic SDK 사용."""
import base64
import json
import anthropic
import app.db as db_module
from app.models import Photo

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "scene": {"type": "string", "description": "사진 장면을 한국어 1문장으로"},
        "location_guess": {"type": "string"},
        "mood": {"type": "string"},
        "people": {"type": "string"},
        "notable_details": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["scene", "location_guess", "mood", "people", "notable_details"],
    "additionalProperties": False,
}


def _small_path(image_path: str) -> str:
    """분석은 항상 리사이즈본(_small.jpg)을 사용한다. 원본은 인쇄용."""
    small = image_path.replace(".jpg", "_small.jpg")
    import os
    return small if os.path.exists(small) else image_path


def analyze_image(image_path: str) -> dict:
    with open(_small_path(image_path), "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    client = anthropic.Anthropic()
    res = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
            {"type": "text", "text": "이 여행 사진에 무엇이 찍혔는지 분석해줘."},
        ]}],
    )
    text = next(b.text for b in res.content if b.type == "text")
    return json.loads(text)


def analyze_and_save(photo_id: str) -> None:
    db = db_module.SessionLocal()
    try:
        photo = db.get(Photo, photo_id)
        if not photo:
            return
        try:
            result = analyze_image(photo.file_path)
            # 왜 scene만 앞에 빼는가: UI 카드에는 1문장만 보여주고, 집필 프롬프트엔 전체 JSON을 쓴다
            photo.ai_scene_description = result["scene"] + "\n" + json.dumps(result, ensure_ascii=False)
            photo.analysis_status = "done"
        except Exception:
            photo.analysis_status = "failed"
        db.commit()
    finally:
        db.close()
