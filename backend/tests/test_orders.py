import httpx


def _ready(client):
    import app.db as db_module
    from app.models import Project, Page
    db = db_module.SessionLocal()
    p = Project(title="t", mood="comedy", status="ready")
    db.add(p); db.commit()
    db.add(Page(project_id=p.id, page_number=1, photo_id=None, text="글" * 260, ai_text="x"))
    db.commit()
    return p.id


def _mock_client():
    from app.sweetbook.client import SweetbookClient
    def handler(req):
        return httpx.Response(200, json={"success": True, "message": "ok",
                                         "data": {"bookUid": "B1", "orderUid": "O1"}})
    return SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler))


def test_order_flow_and_webhook(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = _ready(client)
    res = client.post(f"/api/v1/projects/{pid}/order",
                      json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "이의진"}})
    assert res.status_code == 200
    assert res.json() == {"book_uid": "B1", "order_uid": "O1"}
    assert client.get(f"/api/v1/projects/{pid}/order/status").json()["order_status"] == "ORDERED"
    client.post("/api/v1/webhooks/sweetbook", json={"orderUid": "O1", "status": "SHIPPING"})
    assert client.get(f"/api/v1/projects/{pid}/order/status").json()["order_status"] == "SHIPPING"


def test_order_requires_ready(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = client.post("/api/v1/projects", json={"title": "t", "mood": "comedy"}).json()["id"]
    res = client.post(f"/api/v1/projects/{pid}/order", json={"spec": {}, "shipping": {}})
    assert res.status_code == 409
