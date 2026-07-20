"""집필 결과 검증(사진 매칭/순서/길이). / writer가 호출. / parser의 ParsedPage 사용."""
from app.ai.parser import ParsedPage

MIN_LEN, MAX_LEN = 250, 400


def validate_pages(pages: list[ParsedPage], photo_ids: list[str]) -> list[str]:
    errors: list[str] = []
    used = [p.photo_id for p in pages if p.photo_id]
    for pid in photo_ids:
        if used.count(pid) == 0:
            errors.append(f"사진 {pid}의 페이지가 없습니다")
        elif used.count(pid) > 1:
            errors.append(f"사진 {pid}이 여러 페이지에 등장합니다")
    expected = [p for p in used if p in photo_ids]
    if expected != [p for p in photo_ids if p in used]:
        errors.append("사진 페이지 순서가 사용자가 정한 순서와 다릅니다")
    for i, p in enumerate(pages, 1):
        # 왜: 프롤로그/에필로그(photo_id=None)는 길이 제약이 없음
        if p.photo_id is not None and not (MIN_LEN <= len(p.text) <= MAX_LEN):
            errors.append(f"{i}번째 페이지 길이 {len(p.text)}자 (허용: {MIN_LEN}~{MAX_LEN})")
    return errors
