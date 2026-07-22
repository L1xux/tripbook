import httpx
import pytest
from app.sweetbook.client import SweetbookClient, SweetbookError


def make_client(handler):
    return SweetbookClient(api_key="k", env="sandbox",
                           transport=httpx.MockTransport(handler))


def test_create_book_unwraps_data():
    def handler(req):
        assert req.url.path == "/v1/books"
        assert req.headers["authorization"] == "Bearer k"
        return httpx.Response(200, json={"success": True, "message": "ok",
                                         "data": {"bookUid": "B1"}})
    c = make_client(handler)
    assert c.create_book({"creationType": "TEMPLATE"})["bookUid"] == "B1"


def test_failure_raises():
    def handler(req):
        return httpx.Response(200, json={"success": False, "message": "bad",
                                         "data": None, "errors": ["x"]})
    with pytest.raises(SweetbookError):
        make_client(handler).create_book({})


def test_http_error_translated_to_sweetbook_error():
    """비2xx(500 등)/네트워크 오류도 SweetbookError로 통일돼야 라우터가 502로 감싼다(raw 500 노출 방지)."""
    def handler(req):
        return httpx.Response(500, text="boom")
    with pytest.raises(SweetbookError):
        make_client(handler).create_order({"items": []})


def test_renderer_calls_full_sequence(tmp_path):
    import io
    from PIL import Image
    img = tmp_path / "m.jpg"
    Image.new("RGB", (10, 10)).save(img, "JPEG")

    calls = []
    def handler(req):
        calls.append((req.method, req.url.path))
        # pageMin 0 → 패딩 루프 없음, currentPageCount로 finalize 조건 충족
        return httpx.Response(200, json={"success": True, "message": "ok",
                                         "data": {"bookUid": "B1", "orderUid": "O1",
                                                  "pageMeta": {"pageMin": 0, "currentPageCount": 99}}})
    from app.sweetbook.renderer import TemplateRenderer

    class P:  # 최소 프로젝트 스텁
        title = "t"; id = "p1"; cover_line = None; start_date = "2025.04.12"; end_date = "2025.04.14"
    moments = [type("M", (), {"id": "m1", "file_path": str(img), "caption": "글"})()]
    uid = TemplateRenderer(make_client(handler)).render(P(), moments, {"bookSpecUid": "S1", "coverTemplateUid": "C1", "contentTemplateUid": "T1"})
    assert uid == "B1"
    assert [p for _, p in calls] == [
        "/v1/books", "/v1/books/B1/cover", "/v1/books/B1/contents", "/v1/books/B1/finalization"]


def test_content_uses_breakbefore_page_query():
    """내지는 매 호출 새 페이지로 쌓여야 finalize의 최소 페이지를 채운다(breakBefore=page)."""
    seen = {}
    def handler(req):
        if req.url.path.endswith("/contents"):
            seen["breakBefore"] = req.url.params.get("breakBefore")
        return httpx.Response(200, json={"success": True, "message": "ok", "data": {"result": "inserted"}})
    make_client(handler).add_content("B1", "T1", {"caption": "x"}, {"photo": ("p.jpg", b"x", "image/jpeg")})
    assert seen["breakBefore"] == "page"
