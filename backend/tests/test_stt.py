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
    # 여행 테마 프롬프트는 무음 환각을 유발하므로 더 이상 넘기지 않는다
    assert "prompt" not in calls or not calls["prompt"]


def _stt_client(monkeypatch, response):
    import app.ai.stt as stt
    class Tx:
        @staticmethod
        def create(**kw): return response
    class FakeClient:
        class audio:  # noqa
            transcriptions = Tx
    monkeypatch.setattr(stt, "get_stt_client", lambda: FakeClient())


def test_transcribe_drops_silence_hallucination(monkeypatch, tmp_path):
    """무음에서 Whisper가 지어낸 여행 문장(고 no_speech_prob·저 avg_logprob)은 버려 ''를 준다."""
    import app.ai.stt as stt
    R = type("R", (), {
        "text": "여행 중 찍은 사진들을 보니 그때가 생생하게 떠오른다",  # 환각
        "segments": [{"text": "여행 중 찍은 사진들을 보니…", "no_speech_prob": 0.93, "avg_logprob": -1.6}],
    })()
    _stt_client(monkeypatch, R)
    f = tmp_path / "a.webm"; f.write_bytes(b"x")
    assert stt.transcribe(str(f)) == ""


def test_transcribe_keeps_confident_speech(monkeypatch, tmp_path):
    import app.ai.stt as stt
    R = type("R", (), {
        "text": "무시됨",
        "segments": [{"text": "안녕, ", "no_speech_prob": 0.02, "avg_logprob": -0.3},
                     {"text": "만나서 반가워", "no_speech_prob": 0.03, "avg_logprob": -0.4}],
    })()
    _stt_client(monkeypatch, R)
    f = tmp_path / "a.webm"; f.write_bytes(b"x")
    assert stt.transcribe(str(f)) == "안녕, 만나서 반가워"


def test_transcribe_keeps_quiet_speech_with_low_logprob(monkeypatch, tmp_path):
    """빠르거나 작은 실제 발화(낮은 avg_logprob)는 no_speech_prob가 낮으면 잘리면 안 된다.
    ("안녕 만나서 반가워"의 뒷부분이 잘려 "안녕"만 남던 회귀 방지)"""
    import app.ai.stt as stt
    R = type("R", (), {
        "text": "무시됨",
        "segments": [{"text": "안녕 ", "no_speech_prob": 0.05, "avg_logprob": -0.4},
                     {"text": "만나서 반가워", "no_speech_prob": 0.12, "avg_logprob": -1.35}],
    })()
    _stt_client(monkeypatch, R)
    f = tmp_path / "a.webm"; f.write_bytes(b"x")
    assert stt.transcribe(str(f)) == "안녕 만나서 반가워"
