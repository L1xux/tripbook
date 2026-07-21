def _project_with_photo(client, monkeypatch):
    import app.ai.analysis as analysis, app.ai.caption as caption, io
    from PIL import Image
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    monkeypatch.setattr(caption, "transcribe_and_caption", lambda pid: None)
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    mid = client.post(f"/api/v1/projects/{pid}/photos",
                      files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))]).json()["photos"][0]["id"]
    return pid, mid


def test_delete_moment(client, monkeypatch):
    pid, mid = _project_with_photo(client, monkeypatch)
    assert client.delete(f"/api/v1/moments/{mid}").status_code == 200
    assert client.get(f"/api/v1/projects/{pid}").json()["photos"] == []
    assert client.get(f"/api/v1/moments/{mid}").status_code == 404


def test_delete_project_cascades(client, monkeypatch):
    pid, _ = _project_with_photo(client, monkeypatch)
    client.post(f"/api/v1/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
    assert client.delete(f"/api/v1/projects/{pid}").status_code == 200
    assert client.get(f"/api/v1/projects/{pid}").status_code == 404
