# Tripbook — AI 여행기 책 제작 서비스 설계서

- 작성일: 2026-07-21
- 상태: 사용자 승인 대기
- 목적: Sweetbook 채용 지원 포트폴리오. Sweetbook Book Print API의 실제 파트너 클라이언트 서비스를 구현한다.

## 1. 제품 개요

**Tripbook** — "여행 사진과 몇 줄의 메모가, 한 권의 이야기가 됩니다"

사용자가 여행 사진과 짧은 메모(감정 태그 + 2~3줄)를 올리면, 선택한 무드에 맞춰 AI가 하나의 이어지는 여행기를 집필하고, Sweetbook Book Print API로 실물 책을 주문하는 웹 서비스.

핵심 가치 분업: **사진과 기억은 사용자가, 문장력은 AI가, 인쇄는 Sweetbook API가.**

## 2. 확정된 설계 결정

| 항목 | 결정 | 근거 |
|---|---|---|
| 글의 구조 | 하나의 이어지는 이야기 (사진별 캡션 모음 아님) | 무드/장르가 제대로 살고 책으로 읽는 맛 |
| 무드 | 고정 프리셋 5종 | 프롬프트 품질 보장, 데모 안정성 |
| 서비스 범위 | 로그인 없는 위자드 플로우, UUID URL로 프로젝트 유지 | 면접관 즉시 체험, 개발량 합리화 |
| 글 수정 | 페이지별 직접 수정 + 피드백 기반 재생성 | 인쇄물은 사용자가 최종 확인해야 함 |
| 기술 스택 | FastAPI(Python) + React, SQLite | 채용공고 우대사항 2개 충족, Python SDK 제공 |
| UI | 모바일 퍼스트 반응형 웹 (데스크톱은 센터 카드) | 여행 사진은 폰에 있음. AI스토리교실은 모바일 미지원 → 차별화 |
| Sweetbook 연동 | 접근 C: 템플릿 기반(JSON 자동 조판) + BookRenderer 인터페이스로 격리 | 인쇄 도메인 지식 불필요, PDF 렌더러 확장 여지 |
| 사진 분석 | Haiku 4.5, 업로드 즉시 백그라운드 | 단순 인식 작업, 사진 수 비례 비용 최소화 (~3원/장) |
| 집필/재생성 | Opus 4.8 | 책 품질 결정 단계, 1권당 1회라 비용 부담 적음 |
| 집필 UX | 실시간 페이지 피드 (SSE) — 완성된 페이지를 즉시 읽음 | 대기 화면이 아닌 읽기 화면, 체감 대기 0 |
| 문서화 | 학습용 코드 리딩 문서 필수 (7절) | 개발자 본인이 코드를 읽고 이해하는 것이 요구사항 |

## 3. 아키텍처

```
[모바일 퍼스트 React SPA] ──REST/SSE──> [FastAPI 백엔드]
                                            │
                                            ├──> [Claude API]
                                            │      ├─ Haiku 4.5: 사진 분석 (백그라운드)
                                            │      └─ Opus 4.8: 집필(스트리밍)/재생성
                                            │
                                            ├──> [BookRenderer 인터페이스]
                                            │      └─ TemplateRenderer (MVP)
                                            │      └─ (예약석: PdfRenderer)
                                            │
                                            └──> [SweetbookClient 모듈] ──> Book Print API
                                                   Books · Templates · Orders
                                                   (Sandbox/Live 환경변수 전환)
```

**사용자 플로우 (위자드 5단계):**

1. **여행 정보** — 제목, 기간, 동행자, 무드 프리셋 선택
2. **사진 + 메모** — 업로드(EXIF 날짜로 초기 정렬, 드래그로 순서 조정), 사진마다 감정 태그 + 메모. 업로드 즉시 백그라운드 분석이 돌고, "AI가 본 장면"이 사진 카드에 표시되며 사용자가 탭해서 교정 가능
3. **AI 집필** — 실시간 페이지 피드: 완성되는 페이지가 카드로 하나씩 추가되어 바로 읽음
4. **미리보기 + 퇴고** — 책 넘김 미리보기, 페이지 텍스트 직접 수정 / 피드백 입력 후 페이지별 재생성
5. **주문** — 판형·표지 선택 → Sweetbook 책 생성 + 주문 → 주문번호·상태 표시

## 4. 데이터 모델 (SQLite + SQLAlchemy)

```
Project
├─ id: UUID (URL 키), title, start_date, end_date, companions
├─ mood: enum (family_essay | friendship_saga | fantasy_adventure | lyrical_essay | comedy)
├─ status: draft → writing → ready → ordered
└─ sweetbook_book_id, sweetbook_order_id

Photo (입력)
├─ id, project_id, sort_order, file_path, taken_at (EXIF)
├─ emotion (태그), note (사용자 메모)
├─ ai_scene_description (Haiku 분석 결과)
├─ analysis_status: pending → done | failed
└─ user_scene_correction (사용자 교정, nullable)

Page (출력 — 책의 단위)
├─ id, project_id, page_number
├─ photo_id (nullable — 프롤로그/막간/에필로그는 null)
├─ text (현재본), ai_text (AI 원본), regen_count
```

**핵심 모델링 결정: Photo(입력)와 Page(출력)의 분리.** 이어지는 이야기이므로 AI가 글만 있는 페이지를 추가할 수 있다. 단, 규칙으로 강제한다:

- 모든 사진은 반드시 자기 페이지에, 사용자가 정한 순서대로 배치된다 (검증 로직으로 강제)
- AI가 추가할 수 있는 것은 photo_id가 null인 창작 페이지뿐

## 5. 백엔드 API (FastAPI, `/api/v1`)

```
POST   /projects                        프로젝트 생성
GET    /projects/{id}                   전체 상태 조회
POST   /projects/{id}/photos            사진 업로드 (multipart, EXIF 파싱) → 202, 백그라운드 분석 시작
GET    /projects/{id}/photos/analysis   사진별 분석 상태/결과 폴링
PATCH  /photos/{id}                     메모/감정/장면 교정 수정
PATCH  /projects/{id}/photos/order      드래그 정렬 반영
POST   /projects/{id}/write             집필 시작 → 202
GET    /projects/{id}/write/stream      SSE — 완성 페이지 실시간 푸시
PATCH  /pages/{id}                      페이지 텍스트 직접 수정
POST   /pages/{id}/regenerate           페이지 재생성 (피드백 포함)
POST   /projects/{id}/order             판형/표지 선택 → Sweetbook 책 생성 + 주문
GET    /projects/{id}/order/status      주문 상태 (Sweetbook 프록시)
```

OpenAPI 문서(`/docs`) 자동 생성을 그대로 노출한다 (REST API 설계 역량 증빙).

## 6. AI 파이프라인

### 6.1 사진 분석 (Haiku 4.5)

- 업로드 즉시 백그라운드 태스크로 사진 1장당 1회 호출
- structured outputs로 JSON 응답: `{scene, location_guess, mood, people, notable_details[]}`
- 업로드 전 서버에서 긴 변 ~1100px 리사이즈 (토큰 절약, 장당 약 3원)
- 결과가 "AI가 본 장면"으로 표시, 사용자 교정은 `user_scene_correction`에 저장되어 집필 프롬프트에 반영

### 6.2 집필 (Opus 4.8, 스트리밍)

프롬프트 구성:

- 시스템: 공통 작가 지침 + 무드 프리셋별 스타일 지침
- 유저: 여행 메타데이터 + 사진 목록(순서대로: 분석결과(교정 우선), 감정 태그, 메모)
- 출력: 페이지 단위 구분자가 있는 텍스트 포맷 (스트리밍 파싱 용이) — 서버가 페이지 경계에서 잘라 DB 저장 + SSE 푸시

무드 프리셋 5종: 따뜻한 가족 에세이 / 유쾌한 우정 무용담 / 판타지 모험기 / 서정적 여행 에세이 / 유쾌한 코미디. 각각 별도 스타일 지침을 가지되, 공통 강제 규칙:

- 모든 사진을 주어진 순서대로 정확히 1페이지씩 배정
- 창작 페이지(프롤로그/막간/에필로그)는 photo_id 없음으로 표시
- 메모의 사실관계는 각색하되 왜곡 금지
- 페이지당 250~400자 (조판 제약)

**검증 로직 (수신 완료 후, 코드 레벨):** ① 모든 photo_id 정확히 1회 등장 ② 순서 유지 ③ 길이 제한. 실패 시 오류를 명시해 1회 재시도.

### 6.3 페이지 재생성 (Opus 4.8)

전체 재집필이 아니라 앞뒤 페이지를 문맥으로 주고 해당 페이지만 재작성. 사용자 피드백 텍스트를 프롬프트에 포함.

## 7. 학습용 문서화 (요구사항)

개발자 본인이 코드를 읽으며 이해하는 것이 명시적 요구사항이다. 산출물:

- **`docs/ARCHITECTURE.md`** — 시스템 전체 그림: 요청이 프론트→백엔드→외부 API를 거치는 경로를 시나리오별로 따라가는 문서 (한국어)
- **`docs/CODE_TOUR.md`** — 코드 리딩 가이드: "어떤 순서로 어떤 파일을 읽으면 되는지", 파일별 역할 한 줄 설명, 핵심 함수 포인터 (한국어)
- **모듈 docstring** — 모든 주요 모듈 상단에 "이 파일이 하는 일 / 누가 이 파일을 호출하는가 / 이 파일이 호출하는 것" 3줄 요약
- **왜(why) 주석** — 자명하지 않은 결정 지점에만 이유를 남김 (예: "structured outputs 대신 구분자 포맷을 쓰는 이유: 스트리밍 페이지 파싱")
- **README의 "AI와 함께 만든 과정" 섹션** — CLAUDE.md 규칙, AI가 틀렸고 사람이 잡은 지점 기록 (채용 어필 겸용)

각 구현 단계가 끝날 때마다 해당 부분의 문서를 같이 갱신한다 (마지막에 몰아서 쓰지 않는다).

## 8. Sweetbook 연동

- `sweetbook_client.py` 격리 모듈 — Sweetbook API 호출은 전부 이 모듈 경유
- `BookRenderer` 인터페이스 뒤에 `TemplateRenderer`(MVP: 공용 템플릿 + 페이지 JSON 바인딩) 구현. PdfRenderer는 인터페이스만 예약
- 흐름: 퇴고 완료 → 판형/표지 선택 → 책 생성(Books) → 주문(Orders) → 주문번호 저장, 상태는 프록시 조회
- `SWEETBOOK_ENV` 환경변수로 Sandbox/Live 전환. API 키는 `.env` (리포에는 `.env.example`만)
- 실제 템플릿/판형 ID는 파트너 포털에서 확인 후 설정 파일에 기록 (구현 단계 초기에 확인)

## 9. 에러 처리

- 사진 분석 실패: 해당 사진만 "분석 실패 — 메모만으로 진행" 표시, 전체 흐름 비차단
- 집필 중단: 완성 페이지 보존, "이어서 쓰기"로 남은 페이지만 재개
- Sweetbook 주문 실패: 에러를 사용자 언어로 매핑 (잔액/규격/서버 구분), 주문 전 상태로 복구
- 모든 외부 호출에 타임아웃 + SDK 기본 재시도(지수 백오프)

## 10. 테스트 전략

- **유닛**: 집필 검증 로직, 페이지 스트림 파서, Sweetbook 요청 조립 — LLM 없이 픽스처로
- **통합**: Sweetbook Sandbox 대상 1벌 (CI에서는 mock)
- **E2E 데모 시나리오**: 사진 5장 고정 샘플로 업로드→집필→주문 전 과정 스크립트 (면접 리허설 겸 회귀 테스트)

## 11. 마일스톤

1. **Hello Book**: Sandbox 키로 책 생성→주문 확인 스크립트 (연동 검증)
2. **본 서비스**: 위자드 전체 플로우 (백엔드 → 프론트)
3. **배포 + 문서**: 클라우드 배포, 학습용 문서, README
4. **피날레**: 개발지원금으로 실물 책 1권 Live 주문 → 면접장에 실물 지참

## 12. 범위 제외 (YAGNI)

- 회원가입/로그인, 결제, 다국어, PDF 자체 렌더링(인터페이스만), 이미지 생성(사진은 사용자 것), 관리자 화면
