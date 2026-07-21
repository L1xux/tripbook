# Tripbook 📖

여행 사진과 몇 줄의 메모가, 한 권의 이야기가 됩니다.

사진을 올리고 감정·메모를 붙이면 AI가 하나의 이어지는 여행기로 집필하고,
Sweetbook Book Print API로 실물 책을 주문하는 **모바일 퍼스트 웹 서비스**입니다.

> 스크린샷 / 파트너 포털 주문 캡처: Sandbox 실검증 후 추가 예정
> (`docs/SWEETBOOK_API_FEEDBACK.md`의 "다음 할 일" 참고)

## 어떻게 동작하나

```
[React SPA — 위자드 5단계]
  ① 여행 정보+무드 → ② 사진+메모 → ③ 실시간 집필 피드 → ④ 퇴고 → ⑤ 주문
        │ fetch / EventSource(SSE)
        ▼
[FastAPI + SQLite]
  photos.py ──BackgroundTasks──▶ analysis.py ──▶ Claude Haiku 4.5 (사진 분석)
  writing.py ──asyncio task──▶ writer.py ──▶ Claude Opus 4.8 (집필 스트림)
        │                          │ parser.py(<<<PAGE 마커) → validator.py(검증+재시도)
        │                          └─ events.py(SSE 버스) → 페이지 실시간 피드
  orders.py ──▶ sweetbook/renderer.py ──▶ Sweetbook API (create→cover→contents→finalize→order)
        ◀── webhook (주문 상태 갱신)
```

자세한 요청 경로는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)의 "3가지 여정"을 보세요.

## 실행 방법

### 백엔드

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # 키 채우기: ANTHROPIC_API_KEY, SWEETBOOK_API_KEY, SWEETBOOK_ENV
uvicorn app.main:app --reload   # http://localhost:8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### 테스트 / E2E

```bash
cd backend;  python -m pytest tests/ -v      # 백엔드 24개 테스트 (실키 불필요 — 전부 모킹)
cd frontend; npm test && npm run build
cd backend;  python scripts/demo_e2e.py      # uvicorn 실행 중 + 실키 필요
```

## Claude Code와 함께 만든 과정

이 프로젝트는 계획서(`docs/superpowers/plans/2026-07-21-tripbook.md`)를 태스크 단위로
TDD(실패하는 테스트 → 구현 → 통과 → 커밋)로 진행했습니다. [`CLAUDE.md`](CLAUDE.md)에
프로젝트 규칙(3줄 docstring, CODE_TOUR 갱신, 커밋 컨벤션)이 있습니다.

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
