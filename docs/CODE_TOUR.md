# 코드 투어 — 읽는 순서대로

처음 보는 사람이 이 순서로 파일을 열면 시스템 전체가 이해되도록 배치했다.
각 파일 상단에는 "이 파일이 하는 일 / 누가 호출하는가 / 무엇을 호출하는가" 3줄 docstring이 있다.

## 기반 (설정 · DB · 모델)

1. `backend/app/main.py` — 앱 조립(엔트리포인트). 여기서 시작하세요. **여기서 볼 것:** `create_app()`이 등록하는 라우터 목록 = 기능 지도.
2. `backend/app/config.py` — `.env` 설정 로딩(`get_settings()`). **여기서 볼 것:** `OPENAI_API_KEY`(캡션/감정 제안 + Whisper 전사), SWEETBOOK 키, `SWEETBOOK_WEBHOOK_SECRET`(웹훅 서명 검증 — 비어 있으면 검증 생략), `PUBLIC_WEB_BASE`(인쇄 QR 목적지)가 어디서 오는지.
3. `backend/app/db.py` — DB 엔진/세션(`Base`, `SessionLocal`, `get_db`, `session_scope`). **여기서 볼 것:** `check_same_thread=False`인 이유(백그라운드 태스크), 요청 밖 잡이 쓰는 `session_scope`.
4. `backend/app/models.py` — DB 테이블(Project/Photo=순간/Recipient). **여기서 볼 것:** Photo가 사진+음성+전사+캡션+감정을 한 행에 묶는 구조, status/analysis_status 상태 문자열, `has_audio` 프로퍼티, `emotion_arc`.
5. `backend/app/schemas.py` — 요청/응답 Pydantic 스키마. **여기서 볼 것:** `MomentOut`(caption/transcript/suggested_emotion 포함), `ProjectOut`이 photos/recipients를 함께 내려주는 구조. (`PhotoOut = MomentOut`은 구 라우터 호환용 별칭.)

## API 라우터 (요청 진입점)

6. `backend/app/routers/projects.py` — 프로젝트 생성/조회. **여기서 볼 것:** `get_project_or_404`(다른 라우터가 공용으로 씀).
7. `backend/app/routers/photos.py` — 사진 업로드/음성 업로드/수정/정렬 + 오디오 서빙/공개 순간 조회. **여기서 볼 것:** 원본+리사이즈 저장 후 `analysis.analyze_batch` 백그라운드 실행, `upload_audio`가 `caption.transcribe_and_caption`을 백그라운드로 건다. `moment_audio`(바이트 스니핑으로 content-type), `get_moment`(공개 재생 페이지용, 인증 없음).
8. `backend/app/routers/orders.py` — 수령인 등록/주문 생성/상태/웹훅. **여기서 볼 것:** 책은 `TemplateRenderer.render`로 1회만 렌더하고 나+수령인마다 `_place_order`를 반복 호출(각각 `Idempotency-Key` — 타임아웃 재시도의 이중 차감 차단), `ERR_INSUFFICIENT_CREDIT` → 402 / 그 외 `SweetbookError` → 502 매핑. 웹훅은 `_verify_webhook`(HMAC-SHA256 + 타임스탬프 만료)과 `_should_apply`(늦게 도착한 과거 이벤트가 최신 상태를 되돌리지 않게 하는 `STATUS_RANK` 가드).

## AI 파이프라인

9. `backend/app/ai/oai.py` — OpenAI 클라이언트 팩토리+모델 상수. **여기서 볼 것:** `CHAT_MODEL="gpt-4o-mini"`(캡션·감정·아크 공용), lru_cache로 커넥션 재사용.
10. `backend/app/ai/analysis.py` — 사진 비전 분석(gpt-4o-mini, `response_format` json_schema strict)으로 감정 제안. **여기서 볼 것:** 리사이즈본(_small.jpg) 사용, `analyze_batch`가 스레드풀로 병렬화하는 이유(BackgroundTasks 직렬 실행 회피).
11. `backend/app/ai/stt.py` — 음성 전사(OpenAI Whisper `whisper-1`, `language="ko"`). **여기서 볼 것:** `get_stt_client`가 monkeypatch 대상(테스트에서 교체).
12. `backend/app/ai/caption.py` — 전사→충실한 캡션 편집(gpt-4o-mini). **여기서 볼 것:** `NO_INVENTION` 불변식(원문에 없는 사실·감정 추가 금지), 편집 실패 시 전사 원문을 캡션으로 보존하는 폴백.
12b. `backend/app/ai/arc.py` — 여행 감정 아크 요약(gpt-4o-mini). **여기서 볼 것:** 캡션 있는 순간만 요약, 글귀 없으면 None(지어내지 않음).
13. `backend/app/imaging.py` — 이미지 리사이즈+EXIF 촬영일 추출. **여기서 볼 것:** MAX_EDGE=1100 선택 이유(비전 토큰 절감).

## Sweetbook 연동

14. `backend/app/sweetbook/client.py` — Book Print API HTTP 클라이언트. **여기서 볼 것:** `{success, data, errorCode, errors}` 언랩(에러 봉투를 먼저 읽어야 `errorCode`를 잃지 않는다), `create_order`의 `Idempotency-Key`, transport 주입(테스트 모킹).
15. `backend/app/sweetbook/renderer.py` — 책 조립 렌더러(create→cover→contents→finalize). **여기서 볼 것:** 순간 1개=내지 1페이지(`?breakBefore=page`로 누적), 인쇄용 원본 이미지를 multipart로 첨부, 판형 최소 페이지(24p) 미달 시 여백 패딩. `compose_page_image`가 오디오 있는 순간에 사진 아래 종이색 밴드+QR(→`/v/:id`)을 합성(시그니처). Sandbox 실검증은 `docs/SWEETBOOK_API_FEEDBACK.md`.

## 프론트엔드 (v2 — 음성 캡션 포토북 UI)

> React 19 + Vite. 계정 없음 — 서재 목록은 localStorage에 프로젝트 id만 보관.
> 화면 흐름: 서재(홈) → 카드 덱 ⇄ 그리드 → 순간(글귀+음성 파형) → 책 펼침면 → 주문·선물.
> 비주얼은 확정 목업 `.superpowers/brainstorm/*/content/design-v1.html`(필름/Retro)을 단일 기준으로 옮긴 것.

16. `frontend/src/api.ts` — 백엔드 v2 API 클라이언트. **여기서 볼 것:** 모든 컴포넌트는 이 파일로만 서버와 통신, 타입 `Moment/Recipient/Project/PublicMoment`, `audioUrl`·`getMoment`(공개 재생), 에러 detail을 사용자 메시지로 변환.
17. `frontend/src/lib/library.ts` — 계정 없는 "내 서재". **여기서 볼 것:** localStorage에 여행 id 목록만 보관(`listTrips/addTrip/removeTrip`).
18. `frontend/src/App.tsx` — 라우터: `/`(서재) · `/new`(새 여행) · `/p/:id`(앨범). **여기서 볼 것:** 앨범 내부(덱/그리드/책/주문)는 라우트가 아니라 Album의 state로 전환.
19. `frontend/src/screens/Library.tsx` — 홈 서재(책장 진열). **여기서 볼 것:** 없어진 여행 id를 서재에서 청소하는 로직.
20. `frontend/src/screens/NewTrip.tsx` — 새 여행 + 순간 담기(사진 + 목소리 녹음 + 감정). **여기서 볼 것:** 캡션 폴링은 audio를 올린 순간에만 걸고 done/failed에서 종료(pending 고착 순간 무한로딩 금지).
21. `frontend/src/screens/Album.tsx` — 앨범: 카드 덱 ⇄ 그리드 ⇄ 책 ⇄ 주문. **여기서 볼 것:** `view` state 하나로 4개 화면 전환, 덱 끝의 "책으로 만들기" 엔드카드.
22. `frontend/src/components/Recorder.tsx` — 목소리 녹음 버튼(MediaRecorder). **여기서 볼 것:** 정지 시 Blob을 onRecorded로 넘기고 스트림 트랙 정리.
23. `frontend/src/components/MomentCard.tsx` — 순간 카드(탭→글귀 시트). **여기서 볼 것:** 캡션 없으면 transcript로 폴백, 시그니처(글귀+**실제 음성 파형+재생**+스탬프).
24. `frontend/src/components/AudioWaveform.tsx` — **진짜** 음성 파형+재생. **여기서 볼 것:** 오디오를 Web Audio(`decodeAudioData`)로 디코드해 실제 진폭 막대, 탭 재생/진행, 실패 시 정적 막대 폴백.
25. `frontend/src/screens/Voice.tsx` — 공개 재생 페이지 `/v/:id`(인쇄 QR 목적지). **여기서 볼 것:** `getMoment`로 사진+명조 글귀+파형, 없는 순간엔 "이 순간은 더 이상 없어요".
26. `frontend/src/components/BookPreview.tsx` — 책 펼침면 미리보기(사진|명조 캡션). **여기서 볼 것:** "이대로 인쇄된다"는 신뢰를 주는 spread 레이아웃.
27. `frontend/src/components/OrderSheet.tsx` — 주문 + 선물. **여기서 볼 것:** 연락처·우편번호 입력, 동행자 선물 토글 시 합계 2배, `BOOK_SPEC`(SQUAREBOOK_HC + 일기장A + 빈내지, Sandbox 확정값), 완료 후 `onViewStatus`.
28. `frontend/src/components/OrderStatus.tsx` — 주문 현황(내 책+수령인별 인쇄/배송 상태). **여기서 볼 것:** `getOrderStatus` 폴링(웹훅으로 갱신), 상태 문자열 한국어 매핑.
29. `frontend/src/components/MomentCapture.tsx` — 순간 담기 공용(카메라/갤러리 사진 + 녹음 + 감정 + ✨AI추천). **여기서 볼 것:** NewTrip·AddMoments가 공유, `Camera`(즉석 촬영)·`Recorder` 사용, 감정 제안 폴링.
29b. `frontend/src/components/Camera.tsx` — 여행 중 즉석 카메라 촬영(getUserMedia 라이브→셔터→캔버스 JPEG). **여기서 볼 것:** 후면 카메라(facingMode) 요청, 언마운트 시 트랙 정리, 권한 실패 시 안내.
30. `frontend/src/screens/AddMoments.tsx` — 여행 중 순간 추가(`/p/:id/add`). **여기서 볼 것:** 기존 순간을 불러와 이어서 담기.
