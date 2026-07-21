def _seed_photo(client, monkeypatch):
    import app.ai.analysis as analysis, app.ai.caption as caption
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    monkeypatch.setattr(caption, "transcribe_and_caption", lambda pid: None)
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    m = client.post(f"/api/v1/projects/{pid}/photos",
                    files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))]).json()["photos"][0]
    return m["id"]

def test_audio_404_when_no_audio(client, monkeypatch):
    mid = _seed_photo(client, monkeypatch)
    assert client.get(f"/api/v1/moments/{mid}/audio").status_code == 404

def test_audio_served_with_webm_content_type(client, monkeypatch):
    mid = _seed_photo(client, monkeypatch)
    webm = b"\x1a\x45\xdf\xa3" + b"\x00" * 40  # EBML(webm) 헤더
    client.post(f"/api/v1/moments/{mid}/audio", files=[("file", ("v.m4a", webm, "audio/webm"))])
    r = client.get(f"/api/v1/moments/{mid}/audio")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/webm")
