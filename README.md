# Tripbook 📖

여행 사진과 **그때 내가 한 목소리 한 마디**가, 한 권의 책이 됩니다.

사진을 올리고 목소리로 그 순간을 이야기하면 AI가 전사(Whisper)한 뒤 **말한 원문을 다듬어**
캡션(글귀)으로 담고 — 지어내지 않습니다 — Sweetbook Book Print API로 실물 책을
나 자신과 **선물 수령인**에게 주문하는 **모바일 퍼스트 웹 서비스**입니다.

> 스크린샷 / 파트너 포털 주문 캡처: Sandbox 실검증 후 추가 예정
> (`docs/SWEETBOOK_API_FEEDBACK.md`의 "다음 할 일" 참고)

## 어떻게 동작하나

```
[React SPA — 화면 흐름]
  서재(홈) → 카드 덱 ⇄ 그리드 → 순간(글귀+음성 파형) → 책 펼침면 → 주문·선물
        │ fetch (SSE 없음)
        ▼
[FastAPI + SQLite]
  photos.py ──BackgroundTasks──▶ analysis.py ──▶ Claude Haiku 4.5 (사진 감정 제안)
  photos.py(음성 업로드) ──▶ stt.py ──▶ OpenAI Whisper(whisper-1) 전사
                              └─▶ caption.py ──▶ Claude Haiku 4.5 (원문 충실 캡션 편집, NO_INVENTION)
  orders.py ──▶ sweetbook/renderer.py ──▶ Sweetbook API (create→cover→contents→finalize→order×수령인)
        ◀── webhook (주문 상태 갱신)
```

비주얼은 확정 목업(필름/Retro, `.superpowers/brainstorm/*/content/design-v1.html`)을 단일 기준으로 옮겼습니다.
자세한 요청 경로는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)를 보세요.

## 실행 방법

### 백엔드

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # 키 채우기: ANTHROPIC_API_KEY(캡션·감정), OPENAI_API_KEY(Whisper 전사), SWEETBOOK_API_KEY, SWEETBOOK_ENV
uvicorn app.main:app --reload   # http://localhost:8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

> 주문을 실제로 걸려면 `frontend/src/components/OrderSheet.tsx`의 `BOOK_SPEC`에 있는
> `REPLACE_ME` 3개(bookSpec/cover/content template uid)를 Sweetbook Sandbox 포털 값으로 교체하세요.

### 테스트 / E2E

```bash
cd backend;  python -m pytest tests/ -v      # 백엔드 24개 테스트 (실키 불필요 — 전부 모킹)
cd frontend; npm test && npm run build
cd backend;  python scripts/demo_e2e.py      # uvicorn 실행 중 + 실키 필요
```

## Claude Code와 함께 만든 과정

이 프로젝트는 계획서를 태스크 단위로 TDD(실패하는 테스트 → 구현 → 통과 → 커밋)로 진행했습니다.
초기(`plans/2026-07-21-tripbook.md`, 무드 선택→집필)에서 **"목소리 캡션 포토북 + 선물 주문"으로 피벗**했고,
디자인을 목업으로 반복 확정한 뒤 v2를 백엔드(`plans/…-v2-backend.md`)·프론트엔드(`plans/…-v2-frontend.md`)
두 계획으로 나눠 구현했습니다. [`CLAUDE.md`](CLAUDE.md)에 프로젝트 규칙(3줄 docstring, CODE_TOUR 갱신, 커밋 컨벤션)이 있습니다.

**AI가 틀렸고 사람이 잡은 지점** (git 히스토리에 남아 있음):

- `8bba1a2` — 계획 초안이 리사이즈본만 저장하게 되어 있었음. 인쇄에는 원본급 해상도(300dpi)가
  필요하다는 지적으로 **원본(인쇄용)과 리사이즈본(AI 분석용) 분리 저장**으로 수정.
- `8b82209` — Anthropic 키를 bare env에서 읽어 `.env` 설정과 어긋남 → 앱 settings 경유로 수정.
- `edfc768` — 테스트 conftest의 스코프 없는 monkeypatch와 EventBus 구독자 누수 수정.
- `1ad7214` — 불필요한 socketpair 워크어라운드를 conftest에서 제거.

## 문서

| 문서 | 내용 |
|---|---|
| [`docs/CODE_TOUR.md`](docs/CODE_TOUR.md) | 처음 보는 사람용 — 읽는 순서대로 파일 지도 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 사진 업로드/집필/주문, 3가지 요청 여정 |
| [`docs/SWEETBOOK_API_FEEDBACK.md`](docs/SWEETBOOK_API_FEEDBACK.md) | Sweetbook 연동 피드백 (잘된 점/헤맨 점/제안) |
| [`CLAUDE.md`](CLAUDE.md) | 프로젝트 규칙 (스택·테스트·컨벤션) |
