# Sweetbook Book Print API — 연동 피드백

> Task 9~10에서 클라이언트/렌더러/주문 흐름을 구현하며 정리한 기록.
> ⚠️ **Sandbox 실검증(Task 9 Step 5, Task 16 Step 2)은 실제 API 키가 있어야 수행 가능하며 아직 진행되지 않았다.**
> 아래 [헤맨 점]/[개선 제안] 중 실응답 확인이 필요한 항목은 그렇게 표시했다.

## 잘된 점

- **일관된 응답 봉투** — 모든 엔드포인트가 `{success, message, data, errors?}` 형태라
  클라이언트에서 `_call()` 한 곳으로 언랩/에러 처리를 통일할 수 있었다(`sweetbook/client.py`).
- **Bearer 인증** — `Authorization: Bearer {key}` 단순 헤더 방식이라 httpx 클라이언트 기본 헤더로 끝났다.
- **Sandbox/Live 분리** — Base URL만 다르고 스키마가 같아 `SWEETBOOK_ENV` 하나로 전환 가능.
- **TEMPLATE 방식의 단계 분리** — create→cover→contents→finalize가 명확한 단계라
  렌더러를 순차 호출로 곧게 표현할 수 있었다.

## 헤맨 점

- **cover / contents 파라미터 스키마 미확정** — TEMPLATE의 `templateUid`/`params` 세부 필드는
  문서만으로 확신할 수 없어, 실응답 확인 전까지 `build_cover_payload`/`build_content_payload`
  두 함수에 조립을 격리했다. (⚠️ Sandbox 실응답으로 확정 필요)
- **판형/템플릿 UID 출처** — `bookSpecUid`, `coverTemplateUid`, `contentTemplateUid`의 실제 값은
  파트너 포털에서 확인해야 한다. 현재 프론트 `Step5Order.tsx`의 `BOOK_SPEC`은 `REPLACE_ME` 플레이스홀더.
  (⚠️ 포털 값으로 교체 필요)
- **주문 상태 전이 값** — 웹훅 `status` 문자열(`ORDERED`/`SHIPPING`/…)의 전체 집합과 순서는
  실제 웹훅을 받아봐야 확정된다. 현재는 받은 값을 그대로 로컬에 반영만 한다.

## 개선 제안

- payload 스키마를 응답 예시와 함께 문서에 더 명확히 주면 렌더러 구현 시 왕복이 준다.
- 웹훅 서명/검증 헤더가 있다면 명시가 필요(현재 구현은 orderUid 매칭만 하고 서명 검증은 없음 — 운영 전 보강 대상).
- 에러 `errors` 배열의 코드 체계(문자열 vs 구조화)가 문서화되면 사용자 메시지 매핑이 쉬워진다.

## Sandbox 실검증 결과 (2026-07-21, 실키로 확인)

인증 OK(Bearer). 판형/템플릿 UID: `bookSpecUid=SQUAREBOOK_HC`, `coverTemplateUid=79yjMH3qRPly`(일기장A — taupe/명조, 우리 디자인과 일치), `contentTemplateUid=2mi1ao0Z4Vxl`(공용 빈내지).

**실제 계약(스텁과 다른 부분 — 재구현 필요):**

1. **`POST /books`** — `title`이 **필수**(top-level). `{creationType:"TEMPLATE", bookSpecUid, title}` → 201 `{bookUid, pageMeta{pageMin:24,pageMax:130,pageIncrement:2}}`. → `renderer.py` create에 title 추가함(완료).
2. **`POST /books/{uid}/cover`** — **JSON 아님, `multipart/form-data`**. 필드: `templateUid`, `parameters`(JSON 문자열), 이미지 파일 **`coverPhoto`**. 일기장A parameters 필수: `title`, `dateRange`(+`coverLine`). JSON으로 보내면 **415**.
3. **`POST /books/{uid}/contents`** — 역시 **multipart**. 필드: `templateUid`, `parameters`(JSON: `caption`), 이미지 파일 **`photo`**. **표지가 먼저 있어야** 함(없으면 "표지를 먼저 추가").
4. **`POST /books/{uid}/contents` 페이지 누적** — **`breakBefore`는 쿼리 파라미터**(`?breakBefore=page`). 내지 템플릿 기본값이 `none`(같은 페이지 덮어쓰기)이라, 매 순간을 새 페이지로 쌓으려면 **반드시 `?breakBefore=page`**. (form-data로 보내면 무시됨 — 이게 "24개 넣어도 count 0"의 원인이었음.)
5. **`POST /books/{uid}/finalization`** — 최소 **24페이지**(SQUAREBOOK_HC) 미만이면 400 `ERR_INSUFFICIENT_PAGES`. `?breakBefore=page`로 채우면 정상 누적 → 24p에서 `isValid:true`, finalize 201 확인.
6. **`POST /orders`** — body: `items`(배열, 최소 1개, `{bookUid, quantity}`) + `shipping{recipientName, recipientPhone, address1, postalCode, address2}`. 스키마는 통과 확인됨.

**재구현 완료(2026-07-21):** `client.py` cover/contents를 multipart로, `renderer.py`가 순간별 인쇄용 원본 이미지를 첨부 + `?breakBefore=page` + 24p 미만 시 마지막 사진으로 **여백 패딩**, `orders.py` 주문 body를 `items`+`shipping`로. **실 Sandbox에서 create→cover→contents(패딩)→finalize 완주 확인** (`bk_q0FuDYbVMZwh`, 24p isValid). 백엔드 테스트 19개 그린.

**남은 블로커(코드 아님):**
- **주문 시 `크레딧 계정이 존재하지 않습니다`(ERR_VALIDATION_FAILED)** — 대시보드에 충전금 ₩100,000이 보여도 발생. API 문서에 크레딧 계정 생성/활성화 절차가 없음 → **포털 충전 절차 or Sweetbook 지원(sweet@sweetbook.com) 필요**. (스키마 문제 아님, 계정 프로비저닝.)
- **프론트 주문 폼 부족** — 실주문은 `postalCode`·`recipientPhone`가 필수인데 `OrderSheet`는 이름+주소만 받음 → 우편번호/연락처 입력 추가 필요.

> ⚠️ 대화 중 노출된 실키(SWEETBOOK/OPENAI)는 채팅 로그에 남으므로 검증 후 **로테이션(재발급) 권장**.
