import io
from PIL import Image


def _jpg():
    buf = io.BytesIO(); Image.new("RGB", (1200, 900), "red").save(buf, "JPEG"); return buf.getvalue()


def _project(client):
    return client.post("/api/v1/projects", json={"title": "t"}).json()["id"]


def test_upload_creates_moments(client, monkeypatch):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    pid = _project(client)
    res = client.post(f"/api/v1/projects/{pid}/photos",
                      files=[("files", ("a.jpg", _jpg(), "image/jpeg")), ("files", ("b.jpg", _jpg(), "image/jpeg"))])
    assert res.status_code == 202
    assert [m["sort_order"] for m in res.json()["photos"]] == [0, 1]


def test_patch_moment_and_reorder(client, monkeypatch):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    pid = _project(client)
    ms = client.post(f"/api/v1/projects/{pid}/photos",
                     files=[("files", ("a.jpg", _jpg(), "image/jpeg")), ("files", ("b.jpg", _jpg(), "image/jpeg"))]).json()["photos"]
    a, b = ms[0]["id"], ms[1]["id"]
    assert client.patch(f"/api/v1/moments/{a}", json={"emotion": "평온", "caption": "직접 쓴 캡션"}).status_code == 200
    assert client.patch(f"/api/v1/projects/{pid}/photos/order", json={"photo_ids": [b, a]}).status_code == 200
    got = client.get(f"/api/v1/projects/{pid}").json()["photos"]
    assert [m["id"] for m in got] == [b, a]
    assert got[1]["caption"] == "직접 쓴 캡션"


def test_reorder_rejects_duplicate_ids(client, monkeypatch):
    """[a, a]는 set으로는 {a}와 같아 보이지만 정렬을 꼬이게 한다 — 개수까지 일치해야 한다."""
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    pid = _project(client)
    ms = client.post(f"/api/v1/projects/{pid}/photos",
                     files=[("files", ("a.jpg", _jpg(), "image/jpeg")), ("files", ("b.jpg", _jpg(), "image/jpeg"))]).json()["photos"]
    a, b = ms[0]["id"], ms[1]["id"]
    assert client.patch(f"/api/v1/projects/{pid}/photos/order", json={"photo_ids": [a, a, b]}).status_code == 422
    assert client.patch(f"/api/v1/projects/{pid}/photos/order", json={"photo_ids": [a, a]}).status_code == 422
    # 원래 순서는 훼손되지 않았다
    got = client.get(f"/api/v1/projects/{pid}").json()["photos"]
    assert [m["id"] for m in got] == [a, b]
