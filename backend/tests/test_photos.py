import io
from PIL import Image


def _jpg(size=(2000, 1500)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, "JPEG")
    return buf.getvalue()


def _project(client) -> str:
    return client.post("/api/v1/projects", json={"title": "t", "mood": "comedy"}).json()["id"]


def test_upload_resizes_and_creates_rows(client, monkeypatch, tmp_path):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_and_save", lambda photo_id: None)
    pid = _project(client)
    res = client.post(
        f"/api/v1/projects/{pid}/photos",
        files=[("files", ("a.jpg", _jpg(), "image/jpeg")), ("files", ("b.jpg", _jpg(), "image/jpeg"))],
    )
    assert res.status_code == 202
    photos = res.json()["photos"]
    assert [p["sort_order"] for p in photos] == [0, 1]


def test_patch_photo_and_reorder(client, monkeypatch):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_and_save", lambda photo_id: None)
    pid = _project(client)
    photos = client.post(
        f"/api/v1/projects/{pid}/photos",
        files=[("files", ("a.jpg", _jpg(), "image/jpeg")), ("files", ("b.jpg", _jpg(), "image/jpeg"))],
    ).json()["photos"]
    a, b = photos[0]["id"], photos[1]["id"]
    assert client.patch(f"/api/v1/photos/{a}", json={"note": "바다", "emotion": "행복"}).status_code == 200
    assert client.patch(f"/api/v1/projects/{pid}/photos/order", json={"photo_ids": [b, a]}).status_code == 200
    got = client.get(f"/api/v1/projects/{pid}").json()["photos"]
    assert [p["id"] for p in got] == [b, a]
