"""집필 프롬프트 조립(무드 5종). / writer가 호출. / models의 필드를 읽는다."""
import json

MOOD_STYLES = {
    "family_essay": "따뜻한 가족 에세이. 1인칭 회고 시점으로, 사소한 순간에서 의미를 발견하는 문체. 과장하지 말 것.",
    "friendship_saga": "유쾌한 우정 무용담. 친구들끼리 두고두고 놀릴 수 있는 유머. '아쉬움' 같은 감정도 웃음 포인트로 전환.",
    "fantasy_adventure": "판타지 모험기. 여행자를 모험의 주인공으로, 장소를 왕국과 관문으로 각색하되 메모의 사실은 왜곡하지 말고 은유의 옷만 입힐 것.",
    "lyrical_essay": "서정적 여행 에세이. 감각 묘사 중심의 차분한 문체. 풍경과 감정을 겹쳐 쓸 것.",
    "comedy": "유쾌한 코미디. 상황의 어이없음과 반전을 살리는 경쾌한 문체. 자학개그 환영, 비하는 금지.",
}

FORMAT_RULES = """출력 형식 (반드시 준수):
- 각 페이지는 아래 마커 줄로 시작한다. 마커 앞뒤에 다른 말을 붙이지 않는다.
  <<<PAGE photo=사진ID>>>   ← 사진이 들어가는 페이지
  <<<PAGE photo=none>>>     ← 글만 있는 페이지(프롤로그/막간/에필로그)
- 모든 사진을 입력에 주어진 순서 그대로, 각각 정확히 한 페이지에 배정한다.
- 페이지 본문은 250~400자. 마커와 본문 외에 아무것도 출력하지 않는다.
- 사용자 메모의 사실관계는 각색해도 왜곡하지 않는다."""


def build_system_prompt(mood: str) -> str:
    return (
        "당신은 여행 기록을 한 권의 이어지는 이야기로 집필하는 작가다. "
        "사진별 캡션 모음이 아니라 처음부터 끝까지 흐르는 하나의 서사를 쓴다.\n\n"
        f"문체 지침: {MOOD_STYLES[mood]}\n\n{FORMAT_RULES}"
    )


def build_user_prompt(project, photos) -> str:
    lines = [
        f"여행 제목: {project.title}",
        f"기간: {project.start_date or '미상'} ~ {project.end_date or '미상'}",
        f"동행: {project.companions or '미상'}",
        "", "사진 목록 (이 순서대로 각 1페이지):",
    ]
    for p in photos:
        lines.append(json.dumps({
            "사진ID": p.id, "장면": p.scene or "분석 없음", "감정": p.emotion or "", "메모": p.note or ""
        }, ensure_ascii=False))
    lines.append("\n프롤로그로 시작해 에필로그로 끝나는 하나의 여행기를 써라.")
    return "\n".join(lines)
