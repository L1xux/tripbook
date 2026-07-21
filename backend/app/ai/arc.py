"""여행 감정 요약(감정 아크). / projects 라우터가 호출. / llm(Haiku) 사용.
사용자 캡션(자기 말)만으로 여행 전체 감정의 흐름을 짧게 요약한다 — 창작 금지."""
from app.ai.llm import ANALYSIS_MODEL, first_text, get_client

NO_INVENTION = "캡션에 없는 사실·장소·인물·감정을 새로 지어내지 않는다"


def build_arc_prompt(moments: list[tuple[str | None, str | None]]) -> str:
    """moments = (emotion, caption) 목록. 글귀 있는 순간만 프롬프트에 넣는다."""
    lines = [f"- [{e or '?'}] {c}" for e, c in moments if c]
    return (
        "아래는 한 여행에서 사용자가 남긴 순간들의 감정 태그와 글귀다.\n"
        "이 여행이 어떤 감정의 흐름이었는지 2~3문장으로 담담히 요약하라.\n"
        f"규칙: {NO_INVENTION}. 1인칭, 사용자의 말투를 살린다. 은유·소설체 금지. 요약 본문만 출력한다.\n\n"
        f"순간들:\n" + "\n".join(lines)
    )


def generate_arc(moments: list[tuple[str | None, str | None]]) -> str | None:
    if not any(c for _, c in moments):
        return None  # 글귀가 하나도 없으면 요약할 것이 없다 (지어내지 않는다)
    res = get_client().messages.create(
        model=ANALYSIS_MODEL, max_tokens=400,
        messages=[{"role": "user", "content": build_arc_prompt(moments)}],
    )
    return first_text(res).strip()
