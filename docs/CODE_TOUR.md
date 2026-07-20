# 코드 투어 — 읽는 순서대로

1. `backend/app/main.py` — 앱 조립. 여기서 시작하세요.
2. `backend/app/config.py` — .env 설정 로딩.
3. `backend/app/db.py` — DB 엔진/세션.
4. `backend/app/models.py` — DB 테이블 정의 (Project/Photo/Page).
5. `backend/app/schemas.py` — Pydantic 요청/응답 스키마 (ProjectCreate/ProjectOut).
6. `backend/app/imaging.py` — 이미지 리사이즈+EXIF 촬영일 추출.
7. `backend/app/ai/analysis.py` — 사진 비전 분석(Haiku 4.5 structured outputs)으로 장면/위치/분위기/사람/주요디테일 추출.
8. `backend/app/ai/prompts.py` — 집필 프롬프트 조립 (무드별 시스템/사용자 프롬프트).
9. `backend/app/ai/parser.py` — LLM 스트림 출력을 페이지 단위로 파싱 (<<<PAGE 마커 기반).
10. `backend/app/ai/validator.py` — 파싱된 페이지 검증 (사진 매칭/순서/길이).
11. `backend/app/routers/projects.py` — 프로젝트 생성/조회 API 엔드포인트.
12. `backend/app/routers/photos.py` — 사진 업로드/수정/정렬 API 엔드포인트.
