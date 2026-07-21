import httpx


def _project_with_photo(client, monkeypatch):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/photos", files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))])
    return pid


_ORDER_SEQ = iter(["O-me", "O-mom"])


def _mock_client():
    from app.sweetbook.client import SweetbookClient
    def handler(req):
        data = {"bookUid": "B1"}
        if req.url.path.endswith("/orders"):
            data = {"orderUid": next(_ORDER_SEQ)}
        return httpx.Response(200, json={"success": True, "message": "ok", "data": data})
    return SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler))


def test_gift_order_creates_one_print_per_person(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = _project_with_photo(client, monkeypatch)
    client.post(f"/api/v1/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
    res = client.post(f"/api/v1/projects/{pid}/order",
                      json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 200
    body = res.json()
    assert body["book_uid"] == "B1"
    assert len(body["orders"]) == 2  # 나 + 엄마
    assert client.get(f"/api/v1/projects/{pid}/order/status").json()["order_status"] == "ORDERED"


def test_webhook_updates_project_and_recipient(client, monkeypatch):
    import app.routers.orders as orders
    global _ORDER_SEQ
    # 다른 테스트가 모듈 전역 _ORDER_SEQ를 먼저 소진했을 수 있으므로 이 테스트 전용으로 리셋한다
    _ORDER_SEQ = iter(["O-me-wh", "O-mom-wh"])
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = _project_with_photo(client, monkeypatch)
    client.post(f"/api/v1/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
    res = client.post(f"/api/v1/projects/{pid}/order",
                      json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 200
    body = res.json()
    me_uid = next(o["order_uid"] for o in body["orders"] if o["to"] == "나")
    mom_uid = next(o["order_uid"] for o in body["orders"] if o["to"] == "엄마")

    res = client.post("/api/v1/webhooks/sweetbook", json={"orderUid": mom_uid, "status": "SHIPPING"})
    assert res.status_code == 200
    status = client.get(f"/api/v1/projects/{pid}/order/status").json()
    recipient = next(r for r in status["recipients"] if r["name"] == "엄마")
    assert recipient["order_status"] == "SHIPPING"

    res = client.post("/api/v1/webhooks/sweetbook", json={"orderUid": me_uid, "status": "PRINTING"})
    assert res.status_code == 200
    status = client.get(f"/api/v1/projects/{pid}/order/status").json()
    assert status["order_status"] == "PRINTING"


def test_order_requires_photos(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = client.post("/api/v1/projects", json={"title": "빈 여행"}).json()["id"]
    res = client.post(f"/api/v1/projects/{pid}/order", json={"spec": {}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 409
