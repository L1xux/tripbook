"""사진 비전 분석(Haiku 4.5). / photos 라우터가 백그라운드로 호출. / anthropic SDK 사용."""
import base64
import json
from concurrent.futures import ThreadPoolExecutor
import app.db as db_module
from app.models import Photo
from app.imaging import small_path
from app.ai.oai import CHAT_MODEL, get_oai_client

EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"]

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "scene": {"type": "string", "description": "사진 장면을 한국어 1문장으로"},
        "suggested_emotion": {"type": "string", "enum": EMOTIONS},
    },
    "required": ["scene", "suggested_emotion"],
    "additionalProperties": False,
}


def analyze_image(image_path: str) -> dict:
    # 분석은 항상 리사이즈본(_small.jpg)을 사용한다. 원본은 인쇄용.
    with open(small_path(image_path), "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    res = get_oai_client().chat.completions.create(
        model=CHAT_MODEL,
        response_format={"type": "json_schema", "json_schema": {"name": "emotion_pick", "strict": True, "schema": ANALYSIS_SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "이 여행 사진의 장면과 어울리는 감정 하나를 골라줘."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}},
        ]}],
    )
    return json.loads(res.choices[0].message.content)


def analyze_and_save(photo_id: str) -> None:
    with db_module.session_scope() as db:
        photo = db.get(Photo, photo_id)
        if not photo:
            return
        try:
            r = analyze_image(photo.file_path)
            photo.ai_scene_description = r["scene"]
            photo.suggested_emotion = r["suggested_emotion"]
        except Exception:
            pass  # 감정 제안은 실패해도 무해 — 사용자가 직접 고를 수 있다
        db.commit()


def analyze_batch(photo_ids: list[str]) -> None:
    """업로드 배치를 동시 분석. BackgroundTasks는 태스크를 순차 실행하므로
    사진 N장을 개별 태스크로 걸면 비전 호출이 직렬화된다 — 여기서 스레드로 병렬화."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        # analyze_and_save는 호출 시점에 모듈 전역에서 찾으므로 테스트 monkeypatch도 그대로 탄다
        list(pool.map(lambda pid: analyze_and_save(pid), photo_ids))
