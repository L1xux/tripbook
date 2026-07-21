"""사진 비전 분석(Haiku 4.5). / photos 라우터가 백그라운드로 호출. / anthropic SDK 사용."""
import base64
import json
from concurrent.futures import ThreadPoolExecutor
import app.db as db_module
from app.models import Photo
from app.imaging import small_path
from app.ai.llm import ANALYSIS_MODEL, first_text, get_client

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


def analyze_image(image_path: str) -> dict:
    # 분석은 항상 리사이즈본(_small.jpg)을 사용한다. 원본은 인쇄용.
    with open(small_path(image_path), "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    res = get_client().messages.create(
        model=ANALYSIS_MODEL,
        max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
            {"type": "text", "text": "이 여행 사진에 무엇이 찍혔는지 분석해줘."},
        ]}],
    )
    return json.loads(first_text(res))


def analyze_and_save(photo_id: str) -> None:
    with db_module.session_scope() as db:
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


def analyze_batch(photo_ids: list[str]) -> None:
    """업로드 배치를 동시 분석. BackgroundTasks는 태스크를 순차 실행하므로
    사진 N장을 개별 태스크로 걸면 비전 호출이 직렬화된다 — 여기서 스레드로 병렬화."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        # analyze_and_save는 호출 시점에 모듈 전역에서 찾으므로 테스트 monkeypatch도 그대로 탄다
        list(pool.map(lambda pid: analyze_and_save(pid), photo_ids))
