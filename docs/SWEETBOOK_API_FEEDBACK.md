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

## 다음 할 일(실키 확보 시)

1. `.env`에 실제 `SWEETBOOK_API_KEY` 넣고 `cd backend; python scripts/hello_book.py` 실행.
2. `create_book` 실응답을 보고 cover/contents payload 함수 확정.
3. 포털의 판형/템플릿 UID로 `BOOK_SPEC` 3개 값 교체.
4. 전체 플로우(1→5단계) 통주 테스트 후 포털 "주문 목록" 캡처를 README에 추가.
