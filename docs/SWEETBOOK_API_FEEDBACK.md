# Sweetbook Book Print API — 연동 피드백

> 실제 Sandbox 키로 연동하며 정리한 기록. 스텁 → 실검증 → 실주문까지의 왕복이 그대로 남아 있다.
> 최종 확인 2026-08-05 (공식 문서 대조 + Sandbox 실호출).

## 연동 결과 요약

| 단계 | 결과 |
|---|---|
| 인증 (Bearer) | ✅ |
| 책 렌더 create→cover→contents→finalize | ✅ `bk_q0FuDYbVMZwh` 외 4권, 24p `isValid:true` |
| 주문 생성 `POST /orders` | ✅ **`or_3oKrIwb1C5Ao`** (2026-07-21, `PDF_READY`) |
| 충전금 차감 | ✅ 총액 15,327원 → 차감 16,850원(부가세 10% 가산), 잔액 983,150원 |
| 웹훅 수신 | ⬜ 미등록 — 공개 HTTPS 엔드포인트 배포 후 `PUT /webhooks/config` |

## 잘된 점

- **일관된 응답 봉투** — 모든 엔드포인트가 `{success, message, data, errorCode?, errors?, fieldErrors?}` 형태라
  클라이언트에서 `_call()` 한 곳으로 언랩/에러 처리를 통일할 수 있었다(`sweetbook/client.py`).
  특히 `errorCode`가 문자열 enum이라 `ERR_INSUFFICIENT_CREDIT` → "충전금이 부족해요" 같은
  **사용자 메시지 분기를 문자열 매칭 없이** 만들 수 있었다.
- **Bearer 인증 · 환경 분리** — Base URL만 다르고 스키마가 같아 `SWEETBOOK_ENV` 하나로 전환된다.
  충전금도 Sandbox/Live가 완전히 분리돼 있어 테스트가 운영 잔액을 건드릴 걱정이 없다.
- **TEMPLATE 방식의 단계 분리** — create→cover→contents→finalize가 명확한 단계라
  렌더러를 순차 호출로 곧게 표현할 수 있었다.
- **`Idempotency-Key`** — 결제성 API에서 가장 필요한 장치가 처음부터 제공된다.
  "요청은 타임아웃, 서버에선 성공"인 경우 자체 재시도 로직만으로는 이중 차감을 막을 수 없는데,
  이 헤더 하나로 해결됐다. 주문 문서에 **"반드시 포함하세요"**라고 못박아 둔 것도 좋았다.
- **AI 에이전트용 문서 제공** — `/docs/llms.txt`, `/docs/llms-full.txt`(전 페이지 합본),
  개별 페이지 `.md` URL. 문서를 스크래핑할 필요가 없었고, 연동 후반 작업은
  합본 하나를 컨텍스트에 넣고 진행했다. (2026년 API 문서로서 인상적인 부분.)

## 헤맨 점

- **문서의 발견 경로** — 개발 문서가 검색엔진에 `noindex`라 웹검색으로 닿지 않고,
  랜딩에서도 `/docs/` 링크가 눈에 잘 띄지 않는다. **연동 초반에 이 문서를 못 찾아
  파라미터 스키마를 응답으로 역추적하며 헤맸다.** 문서 자체는 충분했는데 도달을 못 한 경우다.
  → 제안: 파트너 포털 첫 화면과 API Key 발급 화면에 개발 문서·`llms.txt` 링크를 크게.
- **cover / contents가 JSON이 아니라 multipart** — 문서에는 명시돼 있으나
  다른 엔드포인트가 전부 JSON이라 관성으로 JSON을 보내 **415**를 만났다.
- **`breakBefore`가 쿼리 파라미터** — form-data로 보내면 조용히 무시된다.
  내지 템플릿 기본값이 `none`(같은 페이지 덮어쓰기)이라, 이걸 놓치면
  "24개를 넣었는데 페이지 수가 0"이 되고 finalize에서 `ERR_INSUFFICIENT_PAGES`로 튄다.
  → 제안: form-data에 `breakBefore`가 섞여 오면 무시 대신 경고를 주면 좋겠다.
- **충전금 계정 프로비저닝** — 포털에 충전금이 보이는 상태에서도 주문이
  `크레딧 계정이 존재하지 않습니다`로 실패했다. Sandbox 충전금 계정이 별도로 생성된 뒤에야 통과.
  → 제안: 이 에러에 "Sandbox 충전금은 별도이며 포털 > 충전금 > 충전 또는
  `POST /credits/sandbox/charge`로 생성됩니다" 안내를 넣으면 지원 문의 한 건이 줄어든다.
  (`POST /credits/sandbox/charge`의 존재를 이 시점에 알았다면 바로 풀렸을 문제다.)

## 개선 제안

- 웹훅 `secretKey`가 **최초 등록 시 1회만** 전체 노출되고 이후 마스킹되는 정책은 안전하지만,
  분실 시 복구가 "해제 후 재등록"뿐이라 운영 중 재발급이 부담스럽다. 별도 rotate 엔드포인트가 있으면 좋겠다.
- Sandbox에서 주문이 `PAID`에 멈추는 건 합리적이나, `POST /webhooks/test` 외에
  **상태 전이를 강제하는 테스트 엔드포인트**(예: `POST /orders/{uid}/sandbox/advance`)가 있으면
  주문 현황 UI를 실제 전이로 검증할 수 있겠다.
- `GET /credits/transactions`가 페이지네이션·필터를 지원하지 않아(문서에 명시됨) 거래가 쌓이면
  클라이언트가 전량을 받아 처리해야 한다. 다른 목록 API와 동일한 페이지네이션이면 일관될 것 같다.

## 우리 구현이 계약과 어긋났던 곳 (2026-08-05 수정)

문서를 정독하고 대조하니 세 군데가 틀려 있었다 — **전부 "동작은 하는데 언젠가 터지는" 유형**이다.

1. **웹훅 페이로드** — 우리는 평면 `{orderUid, status}`를 기대했는데 실제는
   `{event_uid, event_type, created_at, data:{order_uid, order_status}}`. 실제 웹훅이 왔다면 전부 422였다.
   HMAC-SHA256 서명 검증(`"{timestamp}.{raw body}"`)과 타임스탬프 만료(5분)를 함께 구현.
   재시도가 최대 3회라 순서가 뒤바뀐 재전송이 최신 상태를 되돌리지 않도록 상태 랭크 가드도 넣었다.
2. **`Idempotency-Key` 누락** — 자체 스킵 로직(주문 uid 유무)만 있었다. 타임아웃 재시도 시 이중 차감 위험.
3. **`"ORDERED"`** — 존재하지 않는 상태 문자열을 우리가 지어내 쓰고 있었다.
   응답의 `orderStatus`를 그대로 저장하도록 바꾸고, 프론트 라벨도 실제 enum 11종으로 교체.

## 다음 할 일

- [ ] 공개 HTTPS 엔드포인트 배포 → `PUT /webhooks/config` 등록 → `SWEETBOOK_WEBHOOK_SECRET` 설정
- [ ] `POST /webhooks/test`로 수신·서명 검증 실경로 확인
- [ ] 파트너 포털 주문 화면 캡처를 README에 추가

> ⚠️ 대화 중 노출된 실키(SWEETBOOK/OPENAI)는 채팅 로그에 남으므로 **로테이션(재발급) 권장**.
