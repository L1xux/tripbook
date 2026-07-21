# 코드 투어 — 읽는 순서대로

처음 보는 사람이 이 순서로 파일을 열면 시스템 전체가 이해되도록 배치했다.
각 파일 상단에는 "이 파일이 하는 일 / 누가 호출하는가 / 무엇을 호출하는가" 3줄 docstring이 있다.

## 기반 (설정 · DB · 모델)

1. `backend/app/main.py` — 앱 조립(엔트리포인트). 여기서 시작하세요. **여기서 볼 것:** `create_app()`이 등록하는 라우터 목록 = 기능 지도.
2. `backend/app/config.py` — `.env` 설정 로딩(`get_settings()`). **여기서 볼 것:** `ANTHROPIC_API_KEY`(캡션/감정 제안)와 `OPENAI_API_KEY`(Whisper 전사), SWEETBOOK 키가 어디서 오는지.
3. `backend/app/db.py` — DB 엔진/세션(`Base`, `SessionLocal`, `get_db`, `session_scope`). **여기서 볼 것:** `check_same_thread=False`인 이유(백그라운드 태스크), 요청 밖 잡이 쓰는 `session_scope`.
4. `backend/app/models.py` — DB 테이블(Project/Photo=순간/Recipient). **여기서 볼 것:** Photo가 사진+음성+전사+캡션+감정을 한 행에 묶는 구조, status/analysis_status 상태 문자열. (`Page`는 v1 레거시 스텁 — 사용처 없음, 별도 정리 대상.)
5. `backend/app/schemas.py` — 요청/응답 Pydantic 스키마. **여기서 볼 것:** `MomentOut`(caption/transcript/suggested_emotion 포함), `ProjectOut`이 photos/recipients를 함께 내려주는 구조. (`PhotoOut = MomentOut`은 구 라우터 호환용 별칭.)

## API 라우터 (요청 진입점)

6. `backend/app/routers/projects.py` — 프로젝트 생성/조회. **여기서 볼 것:** `get_project_or_404`(다른 라우터가 공용으로 씀).
7. `backend/app/routers/photos.py` — 사진 업로드/음성 업로드/수정/정렬. **여기서 볼 것:** 원본+리사이즈 저장 후 `analysis.analyze_batch` 백그라운드 실행, `upload_audio`가 `caption.transcribe_and_caption`을 백그라운드로 건다.
8. `backend/app/routers/orders.py` — 수령인 등록/주문 생성/상태/웹훅. **여기서 볼 것:** 책은 `TemplateRenderer.render`로 1회만 렌더하고 나+수령인마다 `create_order`를 반복 호출, `SweetbookError` → 502 매핑.

## AI 파이프라인

9. `backend/app/ai/llm.py` — Anthropic 클라이언트 팩토리+모델 상수. **여기서 볼 것:** `ANALYSIS_MODEL="claude-haiku-4-5"`, lru_cache로 커넥션 풀 재사용(analysis/caption이 공유).
10. `backend/app/ai/analysis.py` — 사진 비전 분석(Haiku 4.5 structured outputs)으로 감정 제안. **여기서 볼 것:** 리사이즈본(_small.jpg) 사용, `analyze_batch`가 스레드풀로 병렬화하는 이유(BackgroundTasks 직렬 실행 회피).
11. `backend/app/ai/stt.py` — 음성 전사(OpenAI Whisper `whisper-1`). **여기서 볼 것:** `get_stt_client`가 monkeypatch 대상(테스트에서 교체).
12. `backend/app/ai/caption.py` — 전사→충실한 캡션 편집. **여기서 볼 것:** `NO_INVENTION` 불변식(원문에 없는 사실·감정 추가 금지), 편집 실패 시 전사 원문을 캡션으로 보존하는 폴백.
13. `backend/app/imaging.py` — 이미지 리사이즈+EXIF 촬영일 추출. **여기서 볼 것:** MAX_EDGE=1100 선택 이유(비전 토큰 절감).

## Sweetbook 연동

14. `backend/app/sweetbook/client.py` — Book Print API HTTP 클라이언트. **여기서 볼 것:** `{success, data, errors}` 언랩, transport 주입(테스트 모킹).
15. `backend/app/sweetbook/renderer.py` — 책 조립 렌더러(create→cover→contents→finalize). **여기서 볼 것:** `build_content_payload`가 순간 1개(사진+캡션)를 페이지 1개로 매핑, payload 조립을 `build_*_payload`로 분리해 스키마 변경을 국소화.

## 프론트엔드 (v2 — 음성 캡션 포토북 UI)

> React 19 + Vite. 계정 없음 — 서재 목록은 localStorage에 프로젝트 id만 보관.
> 화면 흐름: 서재(홈) → 카드 덱 ⇄ 그리드 → 순간(글귀+음성 파형) → 책 펼침면 → 주문·선물.
> 비주얼은 확정 목업 `.superpowers/brainstorm/*/content/design-v1.html`(필름/Retro)을 단일 기준으로 옮긴 것.

16. `frontend/src/api.ts` — 백엔드 v2 API 클라이언트. **여기서 볼 것:** 모든 컴포넌트는 이 파일로만 서버와 통신, 타입 `Moment/Recipient/Project`, 에러 detail을 사용자 메시지로 변환.
17. `frontend/src/lib/library.ts` — 계정 없는 "내 서재". **여기서 볼 것:** localStorage에 여행 id 목록만 보관(`listTrips/addTrip/removeTrip`).
18. `frontend/src/App.tsx` — 라우터: `/`(서재) · `/new`(새 여행) · `/p/:id`(앨범). **여기서 볼 것:** 앨범 내부(덱/그리드/책/주문)는 라우트가 아니라 Album의 state로 전환.
19. `frontend/src/screens/Library.tsx` — 홈 서재(책장 진열). **여기서 볼 것:** 없어진 여행 id를 서재에서 청소하는 로직.
20. `frontend/src/screens/NewTrip.tsx` — 새 여행 + 순간 담기(사진 + 목소리 녹음 + 감정). **여기서 볼 것:** 캡션 폴링은 audio를 올린 순간에만 걸고 done/failed에서 종료(pending 고착 순간 무한로딩 금지).
21. `frontend/src/screens/Album.tsx` — 앨범: 카드 덱 ⇄ 그리드 ⇄ 책 ⇄ 주문. **여기서 볼 것:** `view` state 하나로 4개 화면 전환, 덱 끝의 "책으로 만들기" 엔드카드.
22. `frontend/src/components/Recorder.tsx` — 목소리 녹음 버튼(MediaRecorder). **여기서 볼 것:** 정지 시 Blob을 onRecorded로 넘기고 스트림 트랙 정리.
23. `frontend/src/components/MomentCard.tsx` — 순간 카드(탭→글귀 시트). **여기서 볼 것:** 캡션 없으면 transcript로 폴백, 시그니처(글귀+파형+스탬프).
24. `frontend/src/components/Waveform.tsx` — 앰버 음성 파형. **여기서 볼 것:** 오디오 분석 없이 순간 index 시드로 결정적 막대 생성.
25. `frontend/src/components/BookPreview.tsx` — 책 펼침면 미리보기(사진|명조 캡션). **여기서 볼 것:** "이대로 인쇄된다"는 신뢰를 주는 spread 레이아웃.
26. `frontend/src/components/OrderSheet.tsx` — 주문 + 선물. **여기서 볼 것:** 동행자 선물 토글 시 합계 2배, `BOOK_SPEC`의 `REPLACE_ME`(Sweetbook Sandbox 값으로 교체 필요).
