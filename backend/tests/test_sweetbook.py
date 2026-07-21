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


def test_renderer_calls_full_sequence():
    calls = []
    def handler(req):
        calls.append((req.method, req.url.path))
        return httpx.Response(200, json={"success": True, "message": "ok",
                                         "data": {"bookUid": "B1", "orderUid": "O1"}})
    from app.sweetbook.renderer import TemplateRenderer
    from app.ai.parser import ParsedPage

    class P:  # 최소 프로젝트 스텁
        title = "t"; id = "p1"
    pages = [type("Pg", (), {"photo_id": None, "text": "글", "page_number": 1})()]
    uid = TemplateRenderer(make_client(handler)).render(P(), pages, {"bookSpecUid": "S1"})
    assert uid == "B1"
    assert [p for _, p in calls] == [
        "/v1/books", "/v1/books/B1/cover", "/v1/books/B1/contents", "/v1/books/B1/finalization"]
