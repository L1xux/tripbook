def test_upload_audio_saves_and_starts_pipeline(client, monkeypatch, tmp_path):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    import app.ai.caption as caption
    calls = []
    monkeypatch.setattr(caption, "transcribe_and_caption", lambda pid: calls.append(pid))

    pid = client.post("/api/v1/projects", json={"title": "t"}).json()["id"]
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    photo = client.post(f"/api/v1/projects/{pid}/photos",
                        files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))]).json()["photos"][0]

    res = client.post(f"/api/v1/moments/{photo['id']}/audio",
                      files=[("file", ("v.m4a", b"FAKEAUDIO", "audio/m4a"))])
    assert res.status_code == 202
    assert calls == [photo["id"]]  # 캡션 파이프라인이 이 순간으로 시작됨


def test_transcribe_calls_whisper(monkeypatch, tmp_path):
    import app.ai.stt as stt

    class FakeAudio:
        def create(self, **kw):
            class R: text = "어 바다가 진짜 파랬어"
            return R()
    class FakeClient:
        audio = type("A", (), {"transcriptions": FakeAudio()})()
    monkeypatch.setattr(stt, "get_stt_client", lambda: FakeClient())
    f = tmp_path / "v.m4a"; f.write_bytes(b"x")
    assert stt.transcribe(str(f)) == "어 바다가 진짜 파랬어"


def test_transcribe_passes_korean_language(monkeypatch, tmp_path):
    import app.ai.stt as stt
    calls = {}
    class Tx:
        @staticmethod
        def create(**kw):
            calls.update(kw)
            return type("R", (), {"text": "  안녕  "})()
    class FakeClient:
        class audio:  # noqa
            transcriptions = Tx
    monkeypatch.setattr(stt, "get_stt_client", lambda: FakeClient())
    f = tmp_path / "a.m4a"; f.write_bytes(b"x")
    out = stt.transcribe(str(f))
    assert out == "안녕"
    assert calls["language"] == "ko"
    assert calls["model"] == "whisper-1"
