# 아키텍처 — 요청 경로로 읽는 3가지 여정

이 문서는 개념 다이어그램이 아니라 **코드를 열어 따라가는 지도**다.
각 여정은 "이 순서로 파일을 열면 된다"를 목적으로 한다.

시스템 요약: FastAPI(SQLite) 백엔드가 OpenAI(`gpt-4o-mini` — 사진 감정 제안 + 캡션 편집 + 감정 아크,
Whisper `whisper-1` — 음성 전사)와 Sweetbook Book Print API(TEMPLATE 방식)를 오케스트레이션한다.
"순간(Photo=Moment)" 하나는 사진+사용자 음성+캡션+감정을 한 데이터로 묶고, 주문 시 나 자신과
수령인(Recipient) 각각에게 같은 책을 1권씩 인쇄한다. 프론트엔드(React 19 SPA)는
`docs/CODE_TOUR.md`의 16~30번 항목을 참고.

---

## ① 순간 담기 — 사진 업로드 한 장의 여정

1. **`backend/app/routers/photos.py:upload_photos`** — `POST /api/v1/projects/{id}/photos`(multipart, 여러 장).
   프로젝트 검증(`get_project_or_404`) 후 각 파일마다 원본을 `{data_dir}/photos/{project}/{photo}.jpg`에
   그대로 저장(인쇄용 300dpi 보존)하고, **`backend/app/imaging.py:save_resized`**로 리사이즈본(`_small.jpg`,
   최대 1100px)을 만들며 EXIF `DateTimeOriginal`을 얻는다. 모든 사진에 촬영일이 있으면 그 순서로 초기 정렬.
2. 라우터는 사진마다 DB에 `Photo`(순간) 행을 만들고, 커밋 후 **`background.add_task(analysis.analyze_batch, [...])`**를
   한 번만 걸어 즉시 202를 반환한다.
3. **`backend/app/ai/analysis.py:analyze_batch`** — `ThreadPoolExecutor`로 병렬 분석(BackgroundTasks가 순차 실행이라
   장당 태스크로 걸면 비전 호출이 직렬화되는 것을 피한다). 사진마다 **`analyze_and_save`**가
   리사이즈본을 base64로 실어 `analyze_image`(gpt-4o-mini, `response_format` json_schema strict)를 호출, `scene`(1문장)과
   `suggested_emotion`(감정 태그 6종 중 하나)을 받아 `ai_scene_description`/`suggested_emotion`에 저장.
   실패해도 무해하게 넘어간다(사용자가 감정을 직접 고를 수 있음) — `analysis_status`는 이 단계에서 바뀌지 않는다.
4. **폴링** — `GET /api/v1/projects/{id}/photos/analysis`(`photos.py:analysis_status`)로 각 순간의
   `suggested_emotion`/`caption`/`transcript`/`analysis_status`를 조회. 사용자는
   `PATCH /api/v1/moments/{id}`(`patch_moment`)로 emotion/note/caption을 직접 교정할 수 있다.

## ② 목소리 캡션 — 음성 업로드 한 번의 여정

1. **`backend/app/routers/photos.py:upload_audio`** — `POST /api/v1/moments/{id}/audio`(multipart, 단일 파일).
   음성을 `{data_dir}/audio/{project}/{photo}.m4a`에 저장하고 `audio_path`를 기록, 커밋 후
   **`background.add_task(caption.transcribe_and_caption, photo.id)`**를 걸고 즉시 202(`transcript_pending: true`) 반환.
2. **`backend/app/ai/caption.py:transcribe_and_caption`** — 새 세션(`db_module.session_scope`)에서:
   - **`backend/app/ai/stt.py:transcribe`** — Whisper(`whisper-1`)로 음성을 전사해 `transcript`에 원문 그대로 저장.
   - **`polish_caption(transcript)`** — gpt-4o-mini로 `build_caption_prompt`가 조립한 프롬프트를 호출.
     **불변식**: `NO_INVENTION`("원문에 없는 사실·감정·인물·장소를 추가하지 않는다") — 말투/1인칭 시점 유지,
     "음/어" 같은 군더더기만 정리, 40~120자, 은유·각색·소설체 금지. 결과를 `caption`에 저장.
   - 캡션 편집이 실패하면 전사 원문을 그대로 `caption`으로 보존(감정 보존 우선, 창작 대신 원문 폴백).
   - 전체 성공 시 `analysis_status="done"`, 전사 자체가 실패하면 `"failed"`.
3. **폴링** — ①과 같은 `GET /api/v1/projects/{id}/photos/analysis`를 재사용해 `analysis_status`가
   `done`/`failed`가 될 때까지 대기하고, 완료되면 `caption`(사용자 목소리를 다듬은 캡션)을 화면에 채운다.
   사용자는 `PATCH /api/v1/moments/{id}`로 캡션을 직접 다시 고칠 수 있다.

## ③ 선물 — 다인수 주문 한 번의 여정

1. **`backend/app/routers/orders.py:add_recipient`** — `POST /api/v1/projects/{id}/recipients`로 선물 받을
   사람(이름/주소/전화/선물 메시지)을 프로젝트마다 여러 명 등록. `remove_recipient`로 삭제 가능.
2. **`backend/app/routers/orders.py:create_order`** — `POST /api/v1/projects/{id}/order`. 순간이 하나도 없으면 409.
   `get_sweetbook_client()`로 클라이언트를 얻어(테스트에서 monkeypatch 대상):
   - **`backend/app/sweetbook/renderer.py:TemplateRenderer.render`** — 책은 **1회만 렌더**한다:
     `create_book` → `set_cover`(`build_cover_payload`) → 순간마다 `add_content`(`build_content_payload`,
     한 순간 = 한 페이지: 사진+캡션) → `finalize`. 반환된 `book_uid`를 재사용.
   - 같은 `book_uid`로 **나에게 1권** + **수령인마다 1권**(`project.recipients`를 순회)을
     `_place_order`로 반복 호출 — 인쇄는 N+1번, 렌더는 1번.
     각 호출에는 **`Idempotency-Key`**(`tripbook-{project}-{me|recipient}`)를 붙인다. 요청이 타임아웃됐지만
     서버에선 성공한 경우 재시도가 이중 차감·이중 인쇄로 이어지는 것을 막는 유일한 수단이다.
     `externalRef`에는 `tripbook:{project}:{...}`를 넣어 파트너 포털에서 역추적할 수 있게 한다.
   - **`backend/app/sweetbook/client.py`** — 각 호출은 `{success, data, errorCode, errors}`를 언랩,
     실패 시 `SweetbookError(code=errorCode)`.
   - 매핑: `ERR_INSUFFICIENT_CREDIT` → **402**("충전금이 부족해요"), 그 외 `SweetbookError` → **502**(원문 노출 안 함).
     성공 시 `project.sweetbook_book_id/order_id`, 각 수령인의 `sweetbook_order_id`,
     그리고 **응답의 `orderStatus`를 그대로** `order_status`에 저장(우리가 상태 문자열을 지어내지 않는다).
   - 일부만 실패하면 성공분은 이미 커밋돼 있고 502를 반환한다 — 재시도 시 실패분만 다시 주문한다.
3. **상태 조회** — `GET /api/v1/projects/{id}/order/status`(`order_status`)가 프로젝트와 수령인별 주문 상태를 반환.
   상태값은 Sweetbook enum(`PAID → PDF_READY → CONFIRMED → IN_PRODUCTION → PRODUCTION_COMPLETE → SHIPPED → DELIVERED`,
   그 밖에 `CANCELLED`/`CANCELLED_REFUND`/`ERROR`) 그대로이고, 한국어 라벨은 프론트 `OrderStatus.tsx`가 붙인다.
4. **웹훅 수신** — Sweetbook이 `POST /api/v1/webhooks/sweetbook`으로
   `{event_uid, event_type, created_at, data:{order_uid, order_status, …}}`를 보낸다.
   **`orders.py:webhook`**은 서명 검증에 원문 바이트가 필요해 Pydantic 파싱 대신 raw body를 직접 읽고:
   - **`_verify_webhook`** — `X-Webhook-Signature == "sha256=" + HMAC-SHA256(secret, "{timestamp}.{body}")`,
     타임스탬프 5분 초과 시 거절(replay 방지). `SWEETBOOK_WEBHOOK_SECRET`이 비어 있으면 검증 생략(로컬 전용).
   - **`_should_apply`** — 재시도(최대 3회)로 순서가 뒤바뀐 재전송이 최신 상태를 되돌리지 않게
     `STATUS_RANK`로 거른다. 취소·오류는 흐름 밖이라 항상 반영.
   - `sweetbook_order_id`로 프로젝트 또는 수령인을 찾아(둘 다 조회) 갱신 → 다음 폴링이 새 상태를 받는다.
   - 모르는 주문·상태 없는 이벤트도 **200**으로 받는다 — 4xx면 Sweetbook이 3회 재시도한다.
