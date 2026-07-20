# 코드 투어 — 읽는 순서대로

1. `backend/app/main.py` — 앱 조립. 여기서 시작하세요.
2. `backend/app/config.py` — .env 설정 로딩.
3. `backend/app/db.py` — DB 엔진/세션.
4. `backend/app/models.py` — DB 테이블 정의 (Project/Photo/Page).
5. `backend/app/schemas.py` — Pydantic 요청/응답 스키마 (ProjectCreate/ProjectOut).
6. `backend/app/routers/projects.py` — 프로젝트 생성/조회 API 엔드포인트.
