"""전사한 말을 글귀로 다듬는다.
음성 업로드가 백그라운드로 부른다.
stt와 OpenAI를 쓴다."""
import app.db as db_module
from app.models import Photo
from app.ai.stt import transcribe
from app.ai.oai import CHAT_MODEL, get_oai_client

# 창작 금지 규칙을 프롬프트와 테스트가 같은 문자열로 공유하기 위해 상수로 둔다
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
    res = get_oai_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": build_caption_prompt(transcript)}],
    )
    return (res.choices[0].message.content or "").strip()


def transcribe_and_caption(photo_id: str) -> None:
    with db_module.session_scope() as db:
        photo = db.get(Photo, photo_id)
        if not photo or not photo.audio_path:
            return
        try:
            photo.transcript = transcribe(photo.audio_path)
            if not photo.transcript:
                # 알아들은 말이 없으면 지어내지 않고 캡션을 비운 채 끝낸다
                photo.caption = None
                photo.analysis_status = "done"
                db.commit()
                return
            try:
                # 편집이 빈 문자열을 돌려줘도 침묵하지 않고 전사 원문을 남긴다
                photo.caption = polish_caption(photo.transcript) or photo.transcript
            except Exception:
                # 정리에 실패해도 전사 원문은 남긴다
                photo.caption = photo.transcript
            photo.analysis_status = "done"
        except Exception:
            photo.analysis_status = "failed"
        db.commit()
