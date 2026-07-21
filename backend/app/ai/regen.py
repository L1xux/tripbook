"""페이지 단위 재생성(Opus). / pages 라우터가 호출. / prompts의 무드 지침 재사용."""
from app.ai.llm import ADAPTIVE_THINKING, WRITER_MODEL, first_text, get_client
from app.ai.prompts import MOOD_STYLES
from app.ai.validator import MIN_LEN, MAX_LEN


def regenerate_page_text(project, page, prev_text, next_text, feedback) -> str:
    prompt = (
        f"여행기 '{project.title}'의 한 페이지를 다시 써라.\n"
        f"문체: {MOOD_STYLES[project.mood]}\n"
        f"앞 페이지: {prev_text or '(없음 — 첫 페이지)'}\n"
        f"뒤 페이지: {next_text or '(없음 — 마지막 페이지)'}\n"
        f"현재 페이지: {page.text}\n"
        f"사용자 요청: {feedback}\n"
        f"앞뒤 흐름이 자연스럽게 이어지게 {MIN_LEN}~{MAX_LEN}자로, 본문만 출력하라."
    )
    res = get_client().messages.create(
        model=WRITER_MODEL, max_tokens=2048, thinking=ADAPTIVE_THINKING,
        messages=[{"role": "user", "content": prompt}],
    )
    return first_text(res).strip()
