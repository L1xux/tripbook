"""Sweetbook 웹훅 수신 — 실제 계약(중첩 payload + HMAC 서명) 검증.

계약 출처: https://api.sweetbook.com/docs/api/webhooks · /docs/api/webhook-events
  헤더 X-Webhook-Signature: "sha256=" + HMAC-SHA256(secretKey, "{timestamp}.{raw body}")
  본문 {event_uid, event_type, created_at, data:{order_uid, order_status, ...}}
"""
import hashlib
import hmac
import json
import time

import httpx

SECRET = "whsk_test_secret"


def _order_project(client, monkeypatch):
    """주문까지 끝난 프로젝트를 만들고 (project_id, 내 주문 uid, 엄마 주문 uid)를 돌려준다."""
    import io
    from PIL import Image
    import app.ai.analysis as analysis
    import app.routers.orders as orders
    from app.sweetbook.client import SweetbookClient

    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    seq = iter(["O-me", "O-mom"])

    def handler(req):
        data = {"bookUid": "B1", "pageMeta": {"pageMin": 0, "currentPageCount": 99}}
        if req.url.path.endswith("/orders"):
            data = {"orderUid": next(seq), "orderStatus": "PAID"}
        return httpx.Response(200, json={"success": True, "message": "ok", "data": data})

    monkeypatch.setattr(orders, "get_sweetbook_client",
                        lambda: SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler)))
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/photos", files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))])
    client.post(f"/api/v1/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
    body = client.post(f"/api/v1/projects/{pid}/order",
                       json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}}).json()
    me = next(o["order_uid"] for o in body["orders"] if o["to"] == "나")
    mom = next(o["order_uid"] for o in body["orders"] if o["to"] == "엄마")
    return pid, me, mom


def _event(order_uid: str, status: str, event_type: str = "production.started") -> bytes:
    return json.dumps({
        "event_uid": "evt_1", "event_type": event_type, "created_at": "2026-08-05T00:00:00Z",
        "data": {"order_uid": order_uid, "order_status": status},
    }).encode()


def _post(client, raw: bytes, *, secret: str | None = None, timestamp: int | None = None,
          signature: str | None = None):
    ts = str(timestamp if timestamp is not None else int(time.time()))
    headers = {"Content-Type": "application/json", "X-Webhook-Timestamp": ts,
               "X-Webhook-Event": "production.started", "X-Webhook-Delivery": "wh_1"}
    if signature is not None:
        headers["X-Webhook-Signature"] = signature
    elif secret:
        digest = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={digest}"
    return client.post("/api/v1/webhooks/sweetbook", content=raw, headers=headers)


def _use_secret(monkeypatch, secret: str):
    import app.routers.orders as orders
    from app.config import Settings
    monkeypatch.setattr(orders, "get_settings",
                        lambda: Settings(sweetbook_webhook_secret=secret))


def _status(client, pid):
    return client.get(f"/api/v1/projects/{pid}/order/status").json()


def test_webhook_reads_nested_payload(client, monkeypatch):
    """실제 계약은 {data:{order_uid, order_status}} — 평면 {orderUid,status}가 아니다."""
    _use_secret(monkeypatch, "")  # 시크릿 미설정(로컬 개발) — 서명 검증 생략
    pid, me, mom = _order_project(client, monkeypatch)

    assert _post(client, _event(mom, "SHIPPED", "shipping.departed")).status_code == 200
    assert next(r for r in _status(client, pid)["recipients"] if r["name"] == "엄마")["order_status"] == "SHIPPED"

    assert _post(client, _event(me, "IN_PRODUCTION")).status_code == 200
    assert _status(client, pid)["order_status"] == "IN_PRODUCTION"


def test_webhook_accepts_valid_signature(client, monkeypatch):
    _use_secret(monkeypatch, SECRET)
    pid, me, _ = _order_project(client, monkeypatch)
    assert _post(client, _event(me, "IN_PRODUCTION"), secret=SECRET).status_code == 200
    assert _status(client, pid)["order_status"] == "IN_PRODUCTION"


def test_webhook_rejects_forged_signature(client, monkeypatch):
    """시크릿이 설정돼 있으면 서명이 틀린 요청은 상태를 바꾸지 못한다(주문 상태 위조 차단)."""
    _use_secret(monkeypatch, SECRET)
    pid, me, _ = _order_project(client, monkeypatch)
    res = _post(client, _event(me, "DELIVERED"), signature="sha256=deadbeef")
    assert res.status_code == 401
    assert _status(client, pid)["order_status"] == "PAID"


def test_webhook_rejects_missing_signature(client, monkeypatch):
    _use_secret(monkeypatch, SECRET)
    pid, me, _ = _order_project(client, monkeypatch)
    assert _post(client, _event(me, "DELIVERED")).status_code == 401
    assert _status(client, pid)["order_status"] == "PAID"


def test_webhook_rejects_stale_timestamp(client, monkeypatch):
    """오래된 서명의 재전송(replay)은 거절한다."""
    _use_secret(monkeypatch, SECRET)
    pid, me, _ = _order_project(client, monkeypatch)
    old = int(time.time()) - 3600
    assert _post(client, _event(me, "DELIVERED"), secret=SECRET, timestamp=old).status_code == 401
    assert _status(client, pid)["order_status"] == "PAID"


def test_webhook_ignores_out_of_order_redelivery(client, monkeypatch):
    """재시도(최대 3회)로 뒤늦게 도착한 과거 이벤트가 최신 상태를 되돌리면 안 된다."""
    _use_secret(monkeypatch, "")
    pid, me, _ = _order_project(client, monkeypatch)
    _post(client, _event(me, "SHIPPED", "shipping.departed"))
    assert _post(client, _event(me, "IN_PRODUCTION")).status_code == 200  # 늦게 도착한 과거 이벤트
    assert _status(client, pid)["order_status"] == "SHIPPED"


def test_webhook_applies_cancellation_regardless_of_order(client, monkeypatch):
    """취소·오류는 흐름 밖 상태 — 순서 가드에 막히지 않고 항상 반영된다."""
    _use_secret(monkeypatch, "")
    pid, me, _ = _order_project(client, monkeypatch)
    _post(client, _event(me, "SHIPPED", "shipping.departed"))
    _post(client, _event(me, "CANCELLED_REFUND", "order.cancelled"))
    assert _status(client, pid)["order_status"] == "CANCELLED_REFUND"


def test_webhook_unknown_order_is_acknowledged(client, monkeypatch):
    """모르는 주문이어도 200으로 받는다 — 4xx면 Sweetbook이 3회 재시도한다."""
    _use_secret(monkeypatch, "")
    assert _post(client, _event("or_unknown", "SHIPPED")).status_code == 200
