"""Sandbox 연동 검증 스크립트(마일스톤 1). 실행: cd backend; python scripts/hello_book.py
실제 응답을 보고 build_cover_payload/build_content_payload 스키마를 확정하는 용도."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.config import get_settings
from app.sweetbook.client import SweetbookClient

s = get_settings()
c = SweetbookClient(s.sweetbook_api_key, s.sweetbook_env)
print("== 책 생성 (SQUAREBOOK_HC) ==")
book = c.create_book({"creationType": "TEMPLATE", "bookSpecUid": "SQUAREBOOK_HC", "title": "연결 테스트"})
print(book)  # title 필수 — 없으면 400 ERR_VALIDATION_FAILED (Sandbox 실검증)
# 이후 단계는 위 응답과 파트너 포털의 템플릿/판형 ID를 보고 대화형으로 확장한다.
