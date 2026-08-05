"""판형 조회(하드코딩 제거) · 잔액 사전검증 · 주문 취소 · 상태 폴백.

전부 Sweetbook 실계약 기준(https://api.sweetbook.com/docs):
  가격 = priceBase + ((pageCount - pageMin) / pageIncrement) x pricePerIncrement
  취소는 PAID/PDF_READY만, 배송비 포함 전액 환불.
"""
import json

import httpx

from tests.test_orders import _project_with_photo


SPEC = {
    "bookSpecUid": "SQUAREBOOK_HC", "name": "고화질 스퀘어북 (하드커버)",
    "pageMin": 24, "pageMax": 130, "pageIncrement": 2, "booksPerBox": 8,
    "coverType": "Hardcover", "bindingType": "PUR",
    "priceBase": 12600, "pricePerIncrement": 500,
}


def _client(handler):
    from app.sweetbook.client import SweetbookClient
    return SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler))


def _spec_only_handler(req):
    if req.url.path.endswith("/book-specs/SQUAREBOOK_HC"):
        return httpx.Response(200, json={"success": True, "message": "ok", "data": SPEC})
    return httpx.Response(404, json={"success": False, "message": "nope", "errors": []})


def test_book_spec_endpoint_replaces_frontend_hardcoding(client, monkeypatch):
    """주문서가 쓰던 판형 uid 3개와 단가를 서버가 내려준다."""
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", lambda: _client(_spec_only_handler))
    r = client.get("/api/v1/book-spec")
    assert r.status_code == 200
    b = r.json()
    assert b["spec"]["bookSpecUid"] == "SQUAREBOOK_HC"
    assert b["spec"]["coverTemplateUid"] == "79yjMH3qRPly"
    assert b["spec"]["contentTemplateUid"] == "2mi1ao0Z4Vxl"
    assert b["name"] == "고화질 스퀘어북 (하드커버)"
    assert b["price"] == 12600            # 최소 페이지 기준 한 권 값
    assert b["page_min"] == 24


def test_book_spec_price_grows_with_pages(client, monkeypatch):
    """순간이 많아 24p를 넘으면 증가분 단가가 붙는다(공식대로)."""
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", lambda: _client(_spec_only_handler))
    # 40페이지: 12600 + ((40-24)/2)*500 = 16600
    assert client.get("/api/v1/book-spec?pages=40").json()["price"] == 16600
    # pageMin 미만을 물어도 최소 페이지로 올려서 계산한다(패딩되어 인쇄되므로)
    assert client.get("/api/v1/book-spec?pages=2").json()["price"] == 12600


def test_book_spec_failure_is_502_not_500(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client",
                        lambda: _client(lambda req: httpx.Response(500, text="boom")))
    assert client.get("/api/v1/book-spec").status_code == 502


def _order_flow_handler(state):
    """렌더→견적→주문→취소를 한 핸들러로. state로 견적 결과와 호출 기록을 조작·관찰한다."""
    def handler(req):
        path = req.url.path
        state.setdefault("calls", []).append(f"{req.method} {path}")
        if path.endswith("/orders/estimate"):
            return httpx.Response(200, json={"success": True, "message": "ok", "data": {
                "productAmount": 12600, "shippingFee": 3000, "packagingFee": 0,
                "totalAmount": 15600, "paidCreditAmount": 17160,
                "creditBalance": state["balance"], "creditSufficient": state["sufficient"]}})
        if path.endswith("/cancel"):
            state.setdefault("cancelled", []).append(path.split("/")[-2])
            return httpx.Response(200, json={"success": True, "message": "ok",
                                             "data": {"orderStatus": "CANCELLED_REFUND", "refundAmount": 17160}})
        if path.endswith("/orders"):
            n = len(state.setdefault("orders", []))
            state["orders"].append(json.loads(req.content))
            return httpx.Response(200, json={"success": True, "message": "ok",
                                             "data": {"orderUid": f"O-{n}", "orderStatus": "PAID"}})
        if "/orders/" in path:  # GET /orders/{uid}
            uid = path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"success": True, "message": "ok", "data": {
                "orderUid": uid, "orderStatus": state.get("remote_status", "PAID"),
                "orderStatusDisplay": "표시명"}})
        return httpx.Response(200, json={"success": True, "message": "ok", "data": {
            "bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}})
    return handler


def _ordered_project(client, monkeypatch, state):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", lambda: _client(_order_flow_handler(state)))
    pid = _project_with_photo(client, monkeypatch)
    client.post(f"/api/v1/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
    res = client.post(f"/api/v1/projects/{pid}/order",
                      json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    return pid, res


def test_estimate_blocks_order_before_any_charge(client, monkeypatch):
    """잔액이 부족하면 주문을 한 건도 만들지 않고 402로 끊는다(부분 결제 방지)."""
    state = {"balance": 1000, "sufficient": False}
    pid, res = _ordered_project(client, monkeypatch, state)
    assert res.status_code == 402
    assert "충전금" in res.json()["detail"]
    assert state.get("orders", []) == []          # 결제 호출 자체가 없었다
    assert any("estimate" in c for c in state["calls"])


def test_estimate_passes_then_orders(client, monkeypatch):
    state = {"balance": 900000, "sufficient": True}
    pid, res = _ordered_project(client, monkeypatch, state)
    assert res.status_code == 200
    assert len(state["orders"]) == 2              # 나 + 엄마


def test_cancel_refunds_all_orders(client, monkeypatch):
    """취소는 내 주문과 수령인 주문을 모두 되돌리고 상태를 CANCELLED_REFUND로 남긴다."""
    state = {"balance": 900000, "sufficient": True}
    pid, res = _ordered_project(client, monkeypatch, state)
    assert res.status_code == 200

    r = client.post(f"/api/v1/projects/{pid}/order/cancel", json={"reason": "주소를 잘못 적었어요"})
    assert r.status_code == 200, r.text
    assert sorted(state["cancelled"]) == ["O-0", "O-1"]
    st = client.get(f"/api/v1/projects/{pid}/order/status").json()
    assert st["order_status"] == "CANCELLED_REFUND"
    assert st["recipients"][0]["order_status"] == "CANCELLED_REFUND"
    # 취소 후에는 수령인을 다시 손볼 수 있어야 한다(인쇄가 시작되지 않았으므로)
    rid = client.get(f"/api/v1/projects/{pid}").json()["recipients"][0]["id"]
    assert client.patch(f"/api/v1/recipients/{rid}", json={"address": "새 주소"}).status_code == 200


def test_order_uses_server_spec_when_frontend_sends_none(client, monkeypatch):
    """프론트가 판형 uid를 안 보내면 서버 설정값으로 렌더한다(값이 어긋날 여지를 없앤다)."""
    import app.routers.orders as orders
    state = {"balance": 900000, "sufficient": True}
    seen = {}

    def handler(req):
        if req.url.path.endswith("/books") and req.method == "POST":
            seen.update(json.loads(req.content))
        return _order_flow_handler(state)(req)

    monkeypatch.setattr(orders, "get_sweetbook_client", lambda: _client(handler))
    pid = _project_with_photo(client, monkeypatch)
    r = client.post(f"/api/v1/projects/{pid}/order", json={"shipping": {"name": "나", "address": "부산"}})
    assert r.status_code == 200, r.text
    assert seen["bookSpecUid"] == "SQUAREBOOK_HC"


def test_cancel_without_order_is_409(client, monkeypatch):
    import app.routers.orders as orders
    state = {"balance": 1, "sufficient": True}
    monkeypatch.setattr(orders, "get_sweetbook_client", lambda: _client(_order_flow_handler(state)))
    pid = _project_with_photo(client, monkeypatch)
    assert client.post(f"/api/v1/projects/{pid}/order/cancel", json={"reason": "x"}).status_code == 409


def test_status_falls_back_to_get_order_when_webhook_silent(client, monkeypatch):
    """웹훅 미등록이면 상태가 PAID에 멈춘다 — 조회 시 GET /orders/{uid}로 최신 상태를 당겨온다."""
    state = {"balance": 900000, "sufficient": True}
    pid, res = _ordered_project(client, monkeypatch, state)
    assert res.status_code == 200
    state["remote_status"] = "IN_PRODUCTION"

    st = client.get(f"/api/v1/projects/{pid}/order/status").json()
    assert st["order_status"] == "IN_PRODUCTION"
    assert st["recipients"][0]["order_status"] == "IN_PRODUCTION"
    # 당겨온 값은 DB에도 반영돼, 다음 조회는 원격을 다시 묻지 않아도 최신이다
    state["remote_status"] = "PAID"           # 원격이 과거로 돌아가도
    st2 = client.get(f"/api/v1/projects/{pid}/order/status").json()
    assert st2["order_status"] == "IN_PRODUCTION"   # 웹훅과 같은 순서 가드가 걸린다


def test_status_polling_does_not_hammer_sweetbook(client, monkeypatch):
    """화면은 5초마다 폴링한다 — 원격 조회까지 그 주기로 나가면 창 하나가 분당 24회를 쓴다.
    (general 정책 300 req/분) 원격 조회는 창 주기와 분리해 묶는다."""
    import app.routers.orders as orders
    state = {"balance": 900000, "sufficient": True}
    pid, res = _ordered_project(client, monkeypatch, state)
    assert res.status_code == 200

    def remote_calls():
        return len([c for c in state["calls"] if c.startswith("GET /v1/orders/")])

    client.get(f"/api/v1/projects/{pid}/order/status")
    first = remote_calls()
    assert first > 0                       # 첫 조회는 원격을 확인한다

    for _ in range(5):                     # 화면이 열려 있는 25초 동안의 폴링
        client.get(f"/api/v1/projects/{pid}/order/status")
    assert remote_calls() == first         # 추가 호출 없음

    # 간격이 지나면 다시 확인한다
    orders._last_remote_refresh[pid] = 0.0
    state["remote_status"] = "IN_PRODUCTION"
    body = client.get(f"/api/v1/projects/{pid}/order/status").json()
    assert remote_calls() > first
    assert body["order_status"] == "IN_PRODUCTION"


def test_status_fallback_survives_sweetbook_outage(client, monkeypatch):
    """원격 조회가 실패해도 주문 현황 화면은 떠야 한다(마지막으로 아는 상태로)."""
    state = {"balance": 900000, "sufficient": True}
    pid, res = _ordered_project(client, monkeypatch, state)
    assert res.status_code == 200

    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client",
                        lambda: _client(lambda req: httpx.Response(503, text="down")))
    st = client.get(f"/api/v1/projects/{pid}/order/status")
    assert st.status_code == 200
    assert st.json()["order_status"] == "PAID"
