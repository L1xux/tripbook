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
_LAST_ORDER = {}


def _mock_client():
    import json
    from app.sweetbook.client import SweetbookClient
    def handler(req):
        # 렌더 단계(create/cover/contents/finalize)는 pageMeta로 패딩 루프를 즉시 끝낸다
        data = {"bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}
        if req.url.path.endswith("/orders"):
            _LAST_ORDER.update(json.loads(req.content))
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
    # Sweetbook 주문 스키마: items[] + shipping{recipientName, address1, ...}
    assert _LAST_ORDER["items"][0]["bookUid"] == "B1"
    assert _LAST_ORDER["shipping"]["recipientName"] == "엄마"
    assert _LAST_ORDER["shipping"]["address1"] == "서울"
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


def test_partial_failure_persists_successes_and_retry_is_idempotent(client, monkeypatch):
    """나는 성공·수령인은 실패 → 성공분 보존 + 502. 재시도 시 나는 재주문 안 하고(멱등) 수령인만 재주문."""
    import json
    import app.routers.orders as orders
    from app.sweetbook.client import SweetbookClient
    calls = {"orders": 0, "books": 0}
    state = {"fail_recipient": True}

    def handler(req):
        data = {"bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}
        if req.url.path.endswith("/books"):
            calls["books"] += 1
        if req.url.path.endswith("/orders"):
            calls["orders"] += 1
            name = json.loads(req.content)["shipping"]["recipientName"]
            if name == "엄마" and state["fail_recipient"]:
                return httpx.Response(500, text="boom")
            data = {"orderUid": f"O-{name}"}
        return httpx.Response(200, json={"success": True, "message": "ok", "data": data})

    monkeypatch.setattr(orders, "get_sweetbook_client",
                        lambda: SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler)))
    pid = _project_with_photo(client, monkeypatch)
    client.post(f"/api/v1/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})

    # 1차: 나 성공, 엄마 실패 → 502, 그러나 내 주문은 보존
    r1 = client.post(f"/api/v1/projects/{pid}/order",
                     json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    assert r1.status_code == 502
    assert client.get(f"/api/v1/projects/{pid}/order/status").json()["order_status"] == "ORDERED"

    # 2차 재시도(엄마 성공): 책 재렌더 X, 나 재주문 X, 엄마만 주문
    state["fail_recipient"] = False
    r2 = client.post(f"/api/v1/projects/{pid}/order",
                     json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    assert r2.status_code == 200
    assert len(r2.json()["orders"]) == 2          # 나(기존) + 엄마(신규)
    assert calls["orders"] == 3                    # 1차: 나+엄마실패=2, 2차: 엄마=1 (나는 재주문 안 됨)
    assert calls["books"] == 1                     # 책은 1회만 렌더


def test_order_requires_photos(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = client.post("/api/v1/projects", json={"title": "빈 여행"}).json()["id"]
    res = client.post(f"/api/v1/projects/{pid}/order", json={"spec": {}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 409
