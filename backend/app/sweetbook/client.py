"""Sweetbook Book Print API HTTP 클라이언트. / renderer와 orders 라우터가 호출. / httpx 사용.
cover/contents는 Sandbox 실검증 결과 multipart/form-data(이미지 파일 첨부) 방식이다(docs/SWEETBOOK_API_FEEDBACK.md)."""
import json
import httpx

BASE_URLS = {
    "sandbox": "https://api-sandbox.sweetbook.com/v1",
    "live": "https://api.sweetbook.com/v1",
}


class SweetbookError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None, code: str | None = None):
        super().__init__(message)
        self.errors = errors or []
        self.code = code or ""  # errorCode (예: ERR_INSUFFICIENT_CREDIT) — 라우터가 사용자 메시지로 분기


class SweetbookClient:
    def __init__(self, api_key: str, env: str = "sandbox", transport=None):
        self._http = httpx.Client(
            base_url=BASE_URLS[env],
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
            transport=transport,
        )

    def _unwrap(self, res: httpx.Response) -> dict:
        # 에러 응답도 {success:false, errorCode, message, errors} 봉투로 온다 —
        # raise_for_status를 먼저 하면 errorCode를 잃으므로 본문을 먼저 읽는다.
        try:
            body = res.json()
        except ValueError:
            body = None
        if isinstance(body, dict) and not body.get("success", False):
            raise SweetbookError(body.get("message", "unknown"), body.get("errors"), body.get("errorCode"))
        res.raise_for_status()
        return body["data"]

    def _call(self, method: str, path: str, json: dict | None = None, params: dict | None = None,
              headers: dict | None = None) -> dict:
        try:
            return self._unwrap(self._http.request(method, path, json=json, params=params, headers=headers))
        except httpx.HTTPError as e:  # 타임아웃/연결실패/비2xx → 라우터가 502로 처리하도록 SweetbookError로 통일
            raise SweetbookError(f"Sweetbook 통신 실패: {e}") from e

    def _call_multipart(self, method: str, path: str, data: dict, files: dict, params: dict | None = None) -> dict:
        try:
            return self._unwrap(self._http.request(method, path, data=data, files=files, params=params))
        except httpx.HTTPError as e:
            raise SweetbookError(f"Sweetbook 통신 실패: {e}") from e

    def create_book(self, spec: dict) -> dict:
        return self._call("POST", "/books", json=spec)

    def set_cover(self, book_uid: str, template_uid: str, parameters: dict, files: dict) -> dict:
        # multipart: templateUid + parameters(JSON 문자열) + 이미지 파일(coverPhoto 등)
        return self._call_multipart("POST", f"/books/{book_uid}/cover",
                                    data={"templateUid": template_uid, "parameters": json.dumps(parameters, ensure_ascii=False)},
                                    files=files)

    def add_content(self, book_uid: str, template_uid: str, parameters: dict, files: dict, break_before: str = "page") -> dict:
        # breakBefore는 쿼리 파라미터 — "page"라야 매 호출이 새 페이지로 쌓인다(기본 none은 같은 페이지 덮어쓰기)
        return self._call_multipart("POST", f"/books/{book_uid}/contents",
                                    data={"templateUid": template_uid, "parameters": json.dumps(parameters, ensure_ascii=False)},
                                    files=files, params={"breakBefore": break_before})

    def finalize(self, book_uid: str) -> dict:
        return self._call("POST", f"/books/{book_uid}/finalization")

    # ── 판형·템플릿 (하드코딩 대신 여기서 받아온다) ──────────────────────────
    def list_book_specs(self) -> list:
        return self._call("GET", "/book-specs")

    def get_book_spec(self, book_spec_uid: str) -> dict:
        """판형 상세 {name, priceBase, pricePerIncrement, pageMin/Max/Increment, booksPerBox…}.
        accountUid를 안 보내면 우리 계정의 계약 단가가 반영된다."""
        return self._call("GET", f"/book-specs/{book_spec_uid}")

    def list_templates(self, **params) -> list:
        # bookSpecUid / templateKind(cover|content|divider|publish) / category / limit·offset
        return self._call("GET", "/templates", params=params or None)

    # ── 충전금 ───────────────────────────────────────────────────────────
    def get_credits(self) -> dict:
        """충전금 잔액 {accountUid, balance, currency, env}. 주문 전 잔액 안내·운영 점검용."""
        return self._call("GET", "/credits")

    def list_credit_transactions(self) -> list:
        # 쿼리·페이지네이션 미지원 — 전체를 최근순으로 준다(문서 명시). 자르는 건 호출부 몫.
        return self._call("GET", "/credits/transactions")

    def charge_sandbox_credits(self, amount: int, memo: str = "") -> dict:
        """테스트 충전(항상 test 잔액). 운영 스크립트 전용 — 앱 흐름에서 부르지 않는다."""
        return self._call("POST", "/credits/sandbox/charge", json={"amount": amount, "memo": memo})

    # ── 주문 ─────────────────────────────────────────────────────────────
    def estimate_order(self, payload: dict) -> dict:
        """차감 예정액·잔액·충분 여부를 미리 준다 {paidCreditAmount, creditBalance, creditSufficient…}.
        create_order와 같은 본문을 받으므로 FINALIZED된 bookUid가 있어야 한다."""
        return self._call("POST", "/orders/estimate", json=payload)

    def create_order(self, payload: dict, idempotency_key: str | None = None) -> dict:
        # 같은 키로 재시도하면 Sweetbook이 원 응답을 그대로 돌려준다 — 타임아웃 재시도의 이중 차감을 막는 유일한 수단.
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._call("POST", "/orders", json=payload, headers=headers)

    def get_order(self, order_uid: str) -> dict:
        return self._call("GET", f"/orders/{order_uid}")

    def list_books(self, **params) -> list:
        return self._call("GET", "/books", params=params or None)

    def cancel_order(self, order_uid: str, reason: str, idempotency_key: str | None = None) -> dict:
        """PAID·PDF_READY 상태만 취소 가능하며 배송비 포함 전액이 충전금으로 환불된다.
        환불 이중 처리를 막기 위해 취소에도 멱등 키를 붙인다."""
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._call("POST", f"/orders/{order_uid}/cancel",
                          json={"cancelReason": reason}, headers=headers)

    # ── 웹훅 등록 ────────────────────────────────────────────────────────
    def get_webhook_config(self) -> dict:
        return self._call("GET", "/webhooks/config")

    def put_webhook_config(self, webhook_url: str, events: list | None = None, description: str = "") -> dict:
        """수신 URL 등록(HTTPS만). 최초 등록 때만 secretKey 전체값이 1회 내려온다 — 즉시 저장할 것."""
        body = {"webhookUrl": webhook_url, "events": events, "description": description}
        return self._call("PUT", "/webhooks/config", json=body)

    def delete_webhook_config(self) -> dict:
        return self._call("DELETE", "/webhooks/config")
