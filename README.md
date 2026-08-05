# Tripbook 📖

여행 사진과 **그때 내가 한 목소리 한 마디**가, 한 권의 책이 됩니다.

사진을 올리고 목소리로 그 순간을 이야기하면 AI가 전사(Whisper)한 뒤 **말한 원문을 다듬어**
캡션(글귀)으로 담고 — 지어내지 않습니다 — Sweetbook Book Print API로 실물 책을
나 자신과 **선물 수령인**에게 주문하는 **모바일 퍼스트 웹 서비스**입니다.

## ✨ 시그니처 — "종이책을 펼치면, 그때 내 목소리가 흘러나온다"

- **진짜 목소리가 실물 책에 산다.** 순간마다 인쇄면에 **QR**을 넣어, 스캔하면 공개 페이지 `/v/:id`에서
  **그때의 목소리가 재생**된다. 앱 카드에서도 탭하면 내 녹음이 재생되고, 파형은 **Web Audio로 실제 진폭을
  디코드**한 진짜 파형이다(장식용 아님).
- **AI는 증폭하되 창작하지 않는다.** Whisper 전사 → OpenAI가 *말투 그대로* 캡션 편집(`NO_INVENTION`),
  사진 감정 후보 제안(✨ 추천 칩), 캡션만으로 여행 **감정 아크** 요약 — 전부 사용자의 말에서만.
- **여행 중 계속 담고**(사진+녹음+감정), 다 훑은 뒤 **책으로 만들기 → 주문·선물**로 자연스럽게 잇는다.
- 벤치마크: Remento(목소리 QR 하드커버). 우리는 같은 훅을 **여행 세그먼트**로 가져왔다.

> Sweetbook Sandbox 실연동 완료 — 책 렌더(24p `isValid`)부터 **실주문 `or_3oKrIwb1C5Ao`**(`PDF_READY`,
> 충전금 차감 확인)까지 완주했습니다. 연동 기록과 남은 항목(웹훅 등록)은
> [`docs/SWEETBOOK_API_FEEDBACK.md`](docs/SWEETBOOK_API_FEEDBACK.md)에 있습니다.

## 어떻게 동작하나

```
[React SPA — 화면 흐름]
  서재(홈) → 카드 덱 ⇄ 그리드 → 순간(글귀+음성 파형) → 책 펼침면 → 주문·선물
        │ fetch (SSE 없음)
        ▼
[FastAPI + SQLite]
  photos.py ──BackgroundTasks──▶ analysis.py ──▶ OpenAI gpt-4o-mini (사진 감정 제안 → ✨ 추천 칩)
  photos.py(음성 업로드) ──▶ stt.py ──▶ OpenAI Whisper(whisper-1, ko) 전사
                              └─▶ caption.py ──▶ OpenAI gpt-4o-mini (원문 충실 캡션 편집, NO_INVENTION)
  photos.py ──▶ GET /moments/{id}/audio (오디오 서빙) · GET /moments/{id} (공개 조회) ──▶ /v/:id 재생 페이지
  projects.py ──▶ arc.py ──▶ OpenAI gpt-4o-mini (여행 감정 아크 요약, 캡션 기반)
  orders.py ──▶ sweetbook/renderer.py ──▶ Sweetbook API (create→cover→contents+QR밴드→finalize→order×수령인)
        ◀── webhook (HMAC 서명 검증 → 주문 상태 갱신)
```

비주얼은 확정 목업(필름/Retro, `.superpowers/brainstorm/*/content/design-v1.html`)을 단일 기준으로 옮겼습니다.
자세한 요청 경로는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)를 보세요.

## 실행 방법

### 백엔드

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # backend/.env에 둔다(설정 로딩이 실행 디렉터리 기준)
                          # 키: OPENAI_API_KEY(캡션·감정·Whisper 전사), SWEETBOOK_API_KEY, SWEETBOOK_ENV,
                          #     SWEETBOOK_WEBHOOK_SECRET(웹훅 서명 검증), PUBLIC_WEB_BASE
uvicorn app.main:app --reload --port 8273   # http://localhost:8273
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev -- --port 5273   # http://localhost:5273  (VITE_API_BASE=http://localhost:8273)
```

### 로컬에서 바로 눌러보기 (데모 여행 시드)

백엔드·프론트를 띄운 뒤, 사진·글귀·감정·재생 가능한 음성·감정 아크·주문 현황이 다 채워진
데모 여행을 만들어 전 화면을 눌러볼 수 있다(AI/실키 불필요):

```bash
cd backend; python scripts/seed_demo.py
# 출력된 URL을 브라우저에서 연다:
#   앨범:      http://localhost:5273/p/<id>     (덱·글귀·파형·그리드·책·주문현황)
#   순간 담기:  http://localhost:5273/p/<id>/add
#   공개 재생:  http://localhost:5273/v/<moment-id>   (인쇄 QR 목적지)
```

> 주문에 쓰는 판형·템플릿 uid는 `frontend/src/components/OrderSheet.tsx`의 `BOOK_SPEC`에
> Sandbox 실계약 값으로 들어가 있습니다. 다른 판형을 쓰려면 그 값을 교체하세요.

### 테스트 / E2E

```bash
cd backend;  python -m pytest tests/ -v      # 백엔드 62개 테스트 (실키 불필요 — 전부 모킹)
cd frontend; npm test && npm run build
cd backend;  python scripts/demo_e2e.py      # uvicorn 실행 중 + 실키 필요
```

### Sweetbook 운영·점검 (실키 필요)

```bash
cd backend
python scripts/sweetbook_ops.py credits            # 충전금 잔액 / transactions, charge
python scripts/sweetbook_ops.py specs              # 판형·계약 단가 / templates, books
python scripts/sweetbook_ops.py webhook register https://…/api/v1/webhooks/sweetbook
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
