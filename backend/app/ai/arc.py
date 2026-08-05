"""여행 전체의 감정 흐름을 짧게 요약한다.
projects 라우터가 부른다.
OpenAI를 쓴다.
사용자가 남긴 글귀만으로 여행 전체의 감정 흐름을 짧게 요약한다."""
from app.ai.oai import CHAT_MODEL, get_oai_client

NO_INVENTION = "캡션에 없는 사실·장소·인물·감정을 새로 지어내지 않는다"


def build_arc_prompt(moments: list[tuple[str | None, str | None]]) -> str:
    """감정과 글귀의 목록을 받아, 글귀가 있는 순간만 프롬프트에 넣는다."""
    lines = [f"- [{e or '?'}] {c}" for e, c in moments if c]
    return (
        "아래는 한 여행에서 사용자가 남긴 순간들의 감정 태그와 글귀다.\n"
        "이 여행이 어떤 감정의 흐름이었는지 2~3문장으로 담담히 요약하라.\n"
        f"규칙: {NO_INVENTION}. 1인칭, 사용자의 말투를 살린다. 은유·소설체 금지. 요약 본문만 출력한다.\n\n"
        f"순간들:\n" + "\n".join(lines)
    )


def generate_arc(moments: list[tuple[str | None, str | None]]) -> str | None:
    if not any(c for _, c in moments):
        return None  # 글귀가 하나도 없으면 요약할 것이 없다
    res = get_oai_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": build_arc_prompt(moments)}],
    )
    return (res.choices[0].message.content or "").strip()
