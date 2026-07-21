"""음성 캡션 파이프라인(전사→충실한 편집). / 음성 업로드가 백그라운드로 호출. / stt·llm 사용."""
import app.db as db_module
from app.models import Photo
from app.ai.stt import transcribe
from app.ai.llm import ANALYSIS_MODEL, first_text, get_client

# 왜 별도 상수: 창작 금지 규칙을 프롬프트와 테스트가 같은 문자열로 공유한다
NO_INVENTION = "원문에 없는 사실·감정·인물·장소를 추가하지 않는다"


def build_caption_prompt(transcript: str) -> str:
    return (
        "여행 사진을 보며 사용자가 말한 내용을 그대로 짧은 캡션으로 다듬어라.\n"
        f"규칙: {NO_INVENTION}. 말투와 1인칭 시점을 유지한다. "
        "'음/어' 같은 군더더기와 중복만 정리한다. 40~120자, 1~2문장. "
        "은유·각색·소설체 금지. 캡션 본문만 출력한다.\n\n"
        f"사용자가 말한 것: {transcript}"
    )


def polish_caption(transcript: str) -> str:
    res = get_client().messages.create(
        model=ANALYSIS_MODEL, max_tokens=300,
        messages=[{"role": "user", "content": build_caption_prompt(transcript)}],
    )
    return first_text(res).strip()


def transcribe_and_caption(photo_id: str) -> None:
    with db_module.session_scope() as db:
        photo = db.get(Photo, photo_id)
        if not photo or not photo.audio_path:
            return
        try:
            photo.transcript = transcribe(photo.audio_path)
            try:
                photo.caption = polish_caption(photo.transcript)
            except Exception:
                # 정리 실패 시 전사 원문을 캡션으로 보존 (감정 보존 우선)
                photo.caption = photo.transcript
            photo.analysis_status = "done"
        except Exception:
            photo.analysis_status = "failed"
        db.commit()
