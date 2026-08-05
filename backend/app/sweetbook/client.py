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

    def get_credits(self) -> dict:
        """충전금 잔액 {accountUid, balance, currency, env}. 주문 전 잔액 안내·운영 점검용."""
        return self._call("GET", "/credits")

    def create_order(self, payload: dict, idempotency_key: str | None = None) -> dict:
        # 같은 키로 재시도하면 Sweetbook이 원 응답을 그대로 돌려준다 — 타임아웃 재시도의 이중 차감을 막는 유일한 수단.
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self._call("POST", "/orders", json=payload, headers=headers)

    def get_order(self, order_uid: str) -> dict:
        return self._call("GET", f"/orders/{order_uid}")
