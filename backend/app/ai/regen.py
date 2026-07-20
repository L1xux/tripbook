"""페이지 단위 재생성(Opus). / pages 라우터가 호출. / prompts의 무드 지침 재사용."""
import anthropic
from app.ai.prompts import MOOD_STYLES
from app.ai.validator import MIN_LEN, MAX_LEN
from app.config import get_settings


def regenerate_page_text(project, page, prev_text, next_text, feedback) -> str:
    client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key or None)
    prompt = (
        f"여행기 '{project.title}'의 한 페이지를 다시 써라.\n"
        f"문체: {MOOD_STYLES[project.mood]}\n"
        f"앞 페이지: {prev_text or '(없음 — 첫 페이지)'}\n"
        f"뒤 페이지: {next_text or '(없음 — 마지막 페이지)'}\n"
        f"현재 페이지: {page.text}\n"
        f"사용자 요청: {feedback}\n"
        f"앞뒤 흐름이 자연스럽게 이어지게 {MIN_LEN}~{MAX_LEN}자로, 본문만 출력하라."
    )
    res = client.messages.create(
        model="claude-opus-4-8", max_tokens=2048, thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    return next(b.text for b in res.content if b.type == "text").strip()
