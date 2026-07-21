"""Sweetbook Book Print API HTTP 클라이언트. / renderer와 orders 라우터가 호출. / httpx 사용."""
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
            timeout=30.0,
            transport=transport,
        )

    def _call(self, method: str, path: str, json: dict | None = None) -> dict:
        res = self._http.request(method, path, json=json)
        res.raise_for_status()
        body = res.json()
        if not body.get("success"):
            raise SweetbookError(body.get("message", "unknown"), body.get("errors"))
        return body["data"]

    def create_book(self, spec: dict) -> dict:
        return self._call("POST", "/books", spec)

    def set_cover(self, book_uid: str, payload: dict) -> dict:
        return self._call("POST", f"/books/{book_uid}/cover", payload)

    def add_content(self, book_uid: str, payload: dict) -> dict:
        return self._call("POST", f"/books/{book_uid}/contents", payload)

    def finalize(self, book_uid: str) -> dict:
        return self._call("POST", f"/books/{book_uid}/finalization")

    def create_order(self, payload: dict) -> dict:
        return self._call("POST", "/orders", payload)

    def get_order(self, order_uid: str) -> dict:
        return self._call("GET", f"/orders/{order_uid}")
