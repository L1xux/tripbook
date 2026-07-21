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
11. `backend/app/ai/writer.py` — 집필 작업 실행: Opus 스트림 → 파서 → DB+SSE, 검증 실패 시 재시도.
12. `backend/app/ai/regen.py` — 페이지 단위 재생성(Opus).
13. `backend/app/events.py` — 프로젝트별 SSE 이벤트 버스 (asyncio.Queue 기반 in-memory).
14. `backend/app/routers/projects.py` — 프로젝트 생성/조회 API 엔드포인트.
15. `backend/app/routers/photos.py` — 사진 업로드/수정/정렬 API 엔드포인트.
16. `backend/app/routers/writing.py` — 집필 시작 및 SSE 스트림 라우터.
17. `backend/app/routers/pages.py` — 페이지 수정/재생성 API 엔드포인트.
18. `backend/app/sweetbook/client.py` — Sweetbook Book Print API HTTP 클라이언트.
19. `backend/app/sweetbook/renderer.py` — 책 조립 렌더러(create→cover→contents→finalize).
