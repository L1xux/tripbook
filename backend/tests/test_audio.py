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


def test_moment_out_has_audio_flag(client, monkeypatch):
    """MomentOut(=getProject의 photos)에 has_audio가 실려야 앱 카드가 파형을 게이팅할 수 있다."""
    import app.ai.analysis as analysis, app.ai.caption as caption
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    monkeypatch.setattr(caption, "transcribe_and_caption", lambda pid: None)
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    m = client.post(f"/api/v1/projects/{pid}/photos",
                    files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))]).json()["photos"][0]
    assert m["has_audio"] is False
    client.post(f"/api/v1/moments/{m['id']}/audio",
                files=[("file", ("v.webm", b"\x1a\x45\xdf\xa3" + b"0" * 20, "audio/webm"))])
    got = [p for p in client.get(f"/api/v1/projects/{pid}").json()["photos"] if p["id"] == m["id"]][0]
    assert got["has_audio"] is True


def test_audio_content_type_sniffed_per_format(client, monkeypatch):
    """wav/mp3도 정확한 content-type으로 서빙돼야 브라우저 <audio>가 재생을 거부하지 않는다."""
    wav = b"RIFF\x24\x90\x01\x00WAVE" + b"\x00" * 20        # RIFF....WAVE
    mp3 = b"\xff\xf3\xe4\xc4" + b"\x00" * 20                 # MPEG 프레임 싱크
    for magic, filename, expected in [(wav, "v.wav", "audio/wav"), (mp3, "v.mp3", "audio/mpeg")]:
        mid = _seed_photo(client, monkeypatch)
        client.post(f"/api/v1/moments/{mid}/audio", files=[("file", (filename, magic, "application/octet-stream"))])
        r = client.get(f"/api/v1/moments/{mid}/audio")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(expected), (filename, r.headers["content-type"])


def test_audio_saved_with_uploaded_extension(client, monkeypatch):
    """webm을 .m4a로 저장하면 Whisper 포맷 판별이 틀어진다 — 업로드 확장자를 보존해야 한다."""
    import app.db as db_module
    from app.models import Photo
    mid = _seed_photo(client, monkeypatch)
    client.post(f"/api/v1/moments/{mid}/audio",
                files=[("file", ("v.webm", b"\x1a\x45\xdf\xa3" + b"0" * 20, "audio/webm"))])
    with db_module.SessionLocal() as db:
        assert db.get(Photo, mid).audio_path.endswith(".webm")
