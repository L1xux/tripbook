"""Sweetbook Book Print API를 부르는 HTTP 클라이언트.
renderer와 orders 라우터, 운영 스크립트가 가져다 쓴다.
httpx에 기댄다.
cover와 contents는 이미지 파일을 첨부하는 multipart 방식이다."""
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
        self.code = code or ""  # 라우터가 사용자 메시지를 고르는 데 쓴다


class SweetbookClient:
    def __init__(self, api_key: str, env: str = "sandbox", transport=None):
        self._http = httpx.Client(
            base_url=BASE_URLS[env],
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
            transport=transport,
        )

    def _unwrap(self, res: httpx.Response) -> dict:
        # 에러도 같은 봉투로 오므로 본문을 먼저 읽는다. raise_for_status가 앞서면 errorCode를 잃는다.
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
        except httpx.HTTPError as e:  # 타임아웃과 연결 실패를 라우터가 아는 한 종류로 통일한다
            raise SweetbookError(f"Sweetbook 통신 실패: {e}") from e

    def _call_multipart(self, method: str, path: str, data: dict, files: dict, params: dict | None = None) -> dict:
        try:
            return self._unwrap(self._http.request(method, path, data=data, files=files, params=params))
        except httpx.HTTPError as e:
            raise SweetbookError(f"Sweetbook 통신 실패: {e}") from e

    def create_book(self, spec: dict) -> dict:
        return self._call("POST", "/books", json=spec)

    def set_cover(self, book_uid: str, template_uid: str, parameters: dict, files: dict) -> dict:
        # templateUid와 JSON 문자열 parameters, 그리고 이미지 파일을 함께 보낸다
        return self._call_multipart("POST", f"/books/{book_uid}/cover",
                                    data={"templateUid": template_uid, "parameters": json.dumps(parameters, ensure_ascii=False)},
                                    files=files)

    def add_content(self, book_uid: str, template_uid: str, parameters: dict, files: dict, break_before: str = "page") -> dict:
        # breakBefore는 쿼리 파라미터이며 page라야 새 페이지로 쌓인다. 기본값 none은 같은 페이지에 덮어쓴다.
        return self._call_multipart("POST", f"/books/{book_uid}/contents",
                                    data={"templateUid": template_uid, "parameters": json.dumps(parameters, ensure_ascii=False)},
                                    files=files, params={"breakBefore": break_before})

    def finalize(self, book_uid: str) -> dict:
        return self._call("POST", f"/books/{book_uid}/finalization")

    # ── 판형·템플릿 ──
    def list_book_specs(self) -> list:
        return self._call("GET", "/book-specs")

    def get_book_spec(self, book_spec_uid: str) -> dict:
        """판형 상세. accountUid를 안 보내면 우리 계정의 계약 단가가 반영된다."""
        return self._call("GET", f"/book-specs/{book_spec_uid}")

    def list_templates(self, **params) -> list:
        # bookSpecUid, templateKind, category, limit, offset으로 거를 수 있다
        return self._call("GET", "/templates", params=params or None)

    # ── 충전금 ──
    def get_credits(self) -> dict:
        """충전금 잔액. 주문 전 안내와 운영 점검에 쓴다."""
        return self._call("GET", "/credits")

    def list_credit_transactions(self) -> list:
        # 페이지네이션을 지원하지 않아 전체를 최근순으로 준다. 자르는 것은 호출부 몫이다.
        return self._call("GET", "/credits/transactions")

    def charge_sandbox_credits(self, amount: int, memo: str = "") -> dict:
        """항상 test 잔액에 충전한다. 운영 스크립트 전용이며 앱 흐름에서는 부르지 않는다."""
        return self._call("POST", "/credits/sandbox/charge", json={"amount": amount, "memo": memo})

    # ── 주문 ──
    def estimate_order(self, payload: dict) -> dict:
        """차감 예정액과 잔액, 충분 여부를 미리 알려준다.
        create_order와 같은 본문을 받으므로 최종화된 bookUid가 있어야 한다."""
        return self._call("POST", "/orders/estimate", json=payload)

    def create_order(self, payload: dict, idempotency_key: str | None = None) -> dict:
        # 같은 키로 재시도하면 원 응답이 그대로 돌아온다. 타임아웃 재시도의 이중 차감을 막는 수단이다.
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._call("POST", "/orders", json=payload, headers=headers)

    def get_order(self, order_uid: str) -> dict:
        return self._call("GET", f"/orders/{order_uid}")

    def list_books(self, **params) -> list:
        return self._call("GET", "/books", params=params or None)

    def cancel_order(self, order_uid: str, reason: str, idempotency_key: str | None = None) -> dict:
        """PAID와 PDF_READY 상태만 취소할 수 있고 배송비까지 전액 환불된다.
        환불이 두 번 처리되지 않도록 취소에도 멱등 키를 붙인다."""
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._call("POST", f"/orders/{order_uid}/cancel",
                          json={"cancelReason": reason}, headers=headers)

    # ── 웹훅 등록 ──
    def get_webhook_config(self) -> dict:
        return self._call("GET", "/webhooks/config")

    def put_webhook_config(self, webhook_url: str, events: list | None = None, description: str = "") -> dict:
        """수신 URL을 등록한다. HTTPS만 허용되며 secretKey 전체값은 최초 등록 때 한 번만 내려온다."""
        body = {"webhookUrl": webhook_url, "events": events, "description": description}
        return self._call("PUT", "/webhooks/config", json=body)

    def delete_webhook_config(self) -> dict:
        return self._call("DELETE", "/webhooks/config")
