# 아키텍처 — 요청 경로로 읽는 3가지 여정

이 문서는 개념 다이어그램이 아니라 **코드를 열어 따라가는 지도**다.
각 여정은 "이 순서로 파일을 열면 된다"를 목적으로 한다.

시스템 요약: FastAPI(SQLite) 백엔드가 Claude API(Haiku 4.5 사진 분석, Opus 4.8 집필)와
Sweetbook Book Print API(TEMPLATE 방식)를 오케스트레이션한다. React SPA(모바일 퍼스트)가
위자드 5단계 UI를 제공하고, 집필은 SSE 실시간 페이지 피드로 흐른다.

---

## ① 사진 업로드 한 장의 여정

1. **`frontend/src/steps/Step2Photos.tsx`** — 파일 선택 → `onFiles()` → `api.ts:uploadPhotos(id, files)`가
   `POST /api/v1/projects/{id}/photos`를 multipart로 호출.
2. **`backend/app/routers/photos.py:upload_photos`** — 프로젝트 검증(`get_project_or_404`) 후 각 파일마다:
   - 원본을 `{data_dir}/photos/{project}/{photo}.jpg`에 그대로 저장(인쇄용 300dpi 보존).
   - **`backend/app/imaging.py:save_resized`** — 리사이즈본(`_small.jpg`, 최대 1100px)을 만들고 EXIF `DateTimeOriginal`을 반환.
   - 모든 사진에 촬영일이 있으면 그 순서로 초기 정렬, 아니면 업로드 순서 유지.
3. **BackgroundTasks** — 사진마다 `analysis.analyze_and_save(photo_id)`를 백그라운드로 등록하고, 라우터는 즉시 202 반환.
4. **`backend/app/ai/analysis.py:analyze_and_save`** — 새 세션에서 리사이즈본을 base64로 실어
   `analyze_image`(Haiku 4.5, structured outputs)로 scene/location/mood/people/details를 받아
   `ai_scene_description`(1문장 + 전체 JSON)에 저장, `analysis_status="done"`(예외 시 `"failed"`).
5. **폴링** — `Step2Photos.tsx`의 `useEffect`가 pending이 남은 동안 2초마다
   `GET /api/v1/projects/{id}/photos/analysis`를 호출해 "AI가 본 장면"을 카드에 채운다.
   사용자가 탭하면 `patchPhoto(user_scene_correction)`로 교정.

## ② 집필 한 번의 여정

1. **`frontend/src/steps/Step2Photos.tsx:go`** — "집필 맡기기" → `api.ts:startWriting` → `POST /api/v1/projects/{id}/write`.
2. **`backend/app/routers/writing.py:start_writing`** — `asyncio.create_task(run_writing(project_id))`로 잡을 띄우고 202 반환.
   프론트는 `/p/{id}/writing`으로 이동해 **`Step3Writing.tsx`**가 `EventSource(writeStreamUrl)`로 SSE 구독.
3. **`backend/app/ai/writer.py:run_writing`** — status를 `writing`으로, 기존 페이지 삭제 후:
   - **`app/ai/prompts.py`** `build_system_prompt(mood)` + `build_user_prompt(project, photos)`로 프롬프트 조립.
   - `stream_book_text`(Opus 4.8, adaptive thinking)의 스트림을 **`app/ai/parser.py:PageStreamParser`**에 흘려
     `<<<PAGE photo=...>>>` 마커 기준으로 페이지를 잘라낸다.
   - 페이지가 완성될 때마다 DB에 저장하고 **`app/events.py:bus.publish`**로 `{"type":"page", ...}` 발행.
4. **`backend/app/ai/validator.py:validate_pages`** — 사진 매칭/순서/길이(250~400자) 검증.
   실패하면 오류를 프롬프트에 되먹여 **1회 재시도**, 그래도 실패하면 status를 `draft`로 되돌리고 `{"type":"error"}`.
   성공하면 status `ready` + `{"type":"done"}`.
5. **`backend/app/routers/writing.py:stream`** — `bus.subscribe`한 큐를 SSE(`data: {json}\n\n`)로 흘리다
   done/error에서 종료. **`Step3Writing.tsx`**는 page 이벤트마다 카드를 추가하고, done이면 "퇴고하러 가기" 버튼 노출.

## ③ 주문 한 번의 여정

1. **`frontend/src/steps/Step5Order.tsx:submit`** — 배송 정보 입력 → `api.ts:createOrder(id, BOOK_SPEC, shipping)` →
   `POST /api/v1/projects/{id}/order`.
2. **`backend/app/routers/orders.py:create_order`** — status가 `ready`가 아니면 409.
   `get_sweetbook_client()`로 클라이언트를 얻어(테스트에서 monkeypatch 대상):
   - **`backend/app/sweetbook/renderer.py:TemplateRenderer.render`** — 4단계 순차 호출:
     `create_book` → `set_cover`(`build_cover_payload`) → 페이지마다 `add_content`(`build_content_payload`) → `finalize`.
   - **`backend/app/sweetbook/client.py`** — 각 호출은 `{success, data, errors}`를 언랩, 실패 시 `SweetbookError`.
   - 이어 `create_order`로 주문 생성. `SweetbookError`는 502로 매핑(원문 노출 안 함).
   - 성공 시 `sweetbook_book_id/order_id`, `order_status="ORDERED"`, status `ordered` 저장.
3. **`Step5Order.tsx`** — 주문번호/상태 화면을 띄우고 5초마다 `GET .../order/status`로 로컬 상태 폴링.
4. **웹훅 수신** — Sweetbook이 `POST /api/v1/webhooks/sweetbook {orderUid, status}`를 보내면
   **`orders.py:webhook`**가 `sweetbook_order_id`로 프로젝트를 찾아 `order_status`를 갱신 → 폴링이 새 상태를 받는다.
