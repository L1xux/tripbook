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
_ORDER_KEYS: list[str] = []


def _mock_client():
    import json
    from app.sweetbook.client import SweetbookClient
    def handler(req):
        # 렌더 단계(create/cover/contents/finalize)는 pageMeta로 패딩 루프를 즉시 끝낸다
        data = {"bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}
        if req.url.path.endswith("/orders"):
            _LAST_ORDER.update(json.loads(req.content))
            _ORDER_KEYS.append(req.headers.get("Idempotency-Key", ""))
            data = {"orderUid": next(_ORDER_SEQ), "orderStatus": "PAID"}
        return httpx.Response(200, json={"success": True, "message": "ok", "data": data})
    return SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler))


def test_gift_order_creates_one_print_per_person(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    _ORDER_KEYS.clear()
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
    # 상태는 우리가 지어낸 문자열이 아니라 Sweetbook이 준 orderStatus를 그대로 쓴다
    assert client.get(f"/api/v1/projects/{pid}/order/status").json()["order_status"] == "PAID"
    # 이중 차감 방지 — 주문마다 Idempotency-Key가 있고 사람마다 값이 다르다
    assert all(_ORDER_KEYS) and len(set(_ORDER_KEYS)) == 2


def test_insufficient_credit_maps_to_402(client, monkeypatch):
    """충전금 부족(402 ERR_INSUFFICIENT_CREDIT)은 502가 아니라 402로, 사용자가 알아들을 메시지로."""
    import app.routers.orders as orders
    from app.sweetbook.client import SweetbookClient

    def handler(req):
        data = {"bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}
        if req.url.path.endswith("/orders"):
            return httpx.Response(402, json={
                "success": False, "errorCode": "ERR_INSUFFICIENT_CREDIT",
                "message": "Insufficient Credit",
                "data": {"required": 14300, "balance": 3220.00, "currency": "KRW"},
                "errors": ["잔액이 부족합니다"], "fieldErrors": [],
            })
        return httpx.Response(200, json={"success": True, "message": "ok", "data": data})

    monkeypatch.setattr(orders, "get_sweetbook_client",
                        lambda: SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler)))
    pid = _project_with_photo(client, monkeypatch)
    res = client.post(f"/api/v1/projects/{pid}/order",
                      json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 402
    assert "충전금" in res.json()["detail"]


def test_partial_failure_persists_successes_and_retry_is_idempotent(client, monkeypatch):
    """나는 성공·수령인은 실패 → 성공분 보존 + 502. 재시도 시 나는 재주문 안 하고(멱등) 수령인만 재주문."""
    import json
    import app.routers.orders as orders
    from app.sweetbook.client import SweetbookClient
    calls = {"orders": 0, "books": 0}
    state = {"fail_recipient": True}
    mom_keys: list[str] = []

    def handler(req):
        data = {"bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}
        if req.url.path.endswith("/books"):
            calls["books"] += 1
        if req.url.path.endswith("/orders"):
            calls["orders"] += 1
            name = json.loads(req.content)["shipping"]["recipientName"]
            if name == "엄마":
                mom_keys.append(req.headers.get("Idempotency-Key", ""))
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
    assert client.get(f"/api/v1/projects/{pid}/order/status").json()["order_status"] == "PAID"

    # 2차 재시도(엄마 성공): 책 재렌더 X, 나 재주문 X, 엄마만 주문
    state["fail_recipient"] = False
    r2 = client.post(f"/api/v1/projects/{pid}/order",
                     json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    assert r2.status_code == 200
    assert len(r2.json()["orders"]) == 2          # 나(기존) + 엄마(신규)
    assert calls["orders"] == 3                    # 1차: 나+엄마실패=2, 2차: 엄마=1 (나는 재주문 안 됨)
    assert calls["books"] == 1                     # 책은 1회만 렌더
    # 실패했던 주문의 재시도는 같은 Idempotency-Key로 나간다 —
    # 1차가 타임아웃이었을 뿐 서버에선 성공했더라도 Sweetbook이 이중 차감 없이 원 응답을 돌려준다
    assert len(mom_keys) == 2 and mom_keys[0] == mom_keys[1]


def test_changed_shipping_gets_new_idempotency_key(client, monkeypatch):
    """Sweetbook은 4xx도 키에 24시간 캐시하고, 같은 키+다른 본문은 422로 거부한다.
    잘못된 주소로 실패한 뒤 고쳐서 재시도하면 반드시 새 키가 나가야 한다(고정 키면 24시간 잠김)."""
    import json
    import app.routers.orders as orders
    from app.sweetbook.client import SweetbookClient
    keys: list[str] = []
    state = {"fail": True}

    def handler(req):
        data = {"bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}
        if req.url.path.endswith("/orders"):
            keys.append(req.headers.get("Idempotency-Key", ""))
            if state["fail"]:
                return httpx.Response(400, json={"success": False, "errorCode": "ERR_VALIDATION_FAILED",
                                                 "message": "잘못된 우편번호", "errors": [], "fieldErrors": []})
            data = {"orderUid": "O-1", "orderStatus": "PAID"}
        return httpx.Response(200, json={"success": True, "message": "ok", "data": data})

    monkeypatch.setattr(orders, "get_sweetbook_client",
                        lambda: SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler)))
    pid = _project_with_photo(client, monkeypatch)
    bad = {"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산", "postalCode": "없음"}}
    assert client.post(f"/api/v1/projects/{pid}/order", json=bad).status_code == 502

    state["fail"] = False
    good = {"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산", "postalCode": "48001"}}
    assert client.post(f"/api/v1/projects/{pid}/order", json=good).status_code == 200
    assert len(keys) == 2 and keys[0] != keys[1]  # 본문이 달라졌으니 키도 달라야 한다


def test_patch_recipient_updates_fields(client, monkeypatch):
    """주문 전에는 수령인 정보를 고칠 수 있다 — 삭제+재등록(중복 주문 위험) 대신 수정."""
    pid = _project_with_photo(client, monkeypatch)
    rid = client.post(f"/api/v1/projects/{pid}/recipients",
                      json={"name": "엄마", "address": "서울"}).json()["id"]
    res = client.patch(f"/api/v1/recipients/{rid}",
                       json={"address": "부산 해운대", "postal_code": "48099", "phone": "010-1111-2222"})
    assert res.status_code == 200
    got = next(r for r in client.get(f"/api/v1/projects/{pid}").json()["recipients"] if r["id"] == rid)
    assert got["address"] == "부산 해운대"
    assert got["postal_code"] == "48099"
    assert got["name"] == "엄마"  # 보내지 않은 필드는 유지


def test_ordered_recipient_cannot_be_changed_or_deleted(client, monkeypatch):
    """이미 주문된 수령인은 수정·삭제 모두 409 — 책은 인쇄되는데 주소만 바뀌거나 추적이 사라지는 것을 막는다."""
    import app.routers.orders as orders
    global _ORDER_SEQ
    _ORDER_SEQ = iter(["O-me-g", "O-mom-g"])
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = _project_with_photo(client, monkeypatch)
    rid = client.post(f"/api/v1/projects/{pid}/recipients",
                      json={"name": "엄마", "address": "서울"}).json()["id"]
    assert client.post(f"/api/v1/projects/{pid}/order",
                       json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}}).status_code == 200

    assert client.patch(f"/api/v1/recipients/{rid}", json={"address": "다른 주소"}).status_code == 409
    assert client.delete(f"/api/v1/recipients/{rid}").status_code == 409
    # 수령인은 그대로 남아 주문 추적이 유지된다
    got = client.get(f"/api/v1/projects/{pid}").json()["recipients"]
    assert [r["id"] for r in got] == [rid]
    assert got[0]["address"] == "서울"


def test_order_requires_photos(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = client.post("/api/v1/projects", json={"title": "빈 여행"}).json()["id"]
    res = client.post(f"/api/v1/projects/{pid}/order", json={"spec": {}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 409
