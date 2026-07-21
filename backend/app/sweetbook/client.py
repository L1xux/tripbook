"""Sweetbook Book Print API HTTP 클라이언트. / renderer와 orders 라우터가 호출. / httpx 사용.
cover/contents는 Sandbox 실검증 결과 multipart/form-data(이미지 파일 첨부) 방식이다(docs/SWEETBOOK_API_FEEDBACK.md)."""
import json
import httpx

BASE_URLS = {
    "sandbox": "https://api-sandbox.sweetbook.com/v1",
    "live": "https://api.sweetbook.com/v1",
}


class SweetbookError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class SweetbookClient:
    def __init__(self, api_key: str, env: str = "sandbox", transport=None):
        self._http = httpx.Client(
            base_url=BASE_URLS[env],
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
            transport=transport,
        )

    def _unwrap(self, res: httpx.Response) -> dict:
        res.raise_for_status()
        body = res.json()
        if not body.get("success"):
            raise SweetbookError(body.get("message", "unknown"), body.get("errors"))
        return body["data"]

    def _call(self, method: str, path: str, json: dict | None = None, params: dict | None = None) -> dict:
        return self._unwrap(self._http.request(method, path, json=json, params=params))

    def _call_multipart(self, method: str, path: str, data: dict, files: dict, params: dict | None = None) -> dict:
        return self._unwrap(self._http.request(method, path, data=data, files=files, params=params))

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

    def create_order(self, payload: dict) -> dict:
        return self._call("POST", "/orders", json=payload)

    def get_order(self, order_uid: str) -> dict:
        return self._call("GET", f"/orders/{order_uid}")
