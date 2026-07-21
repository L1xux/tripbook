def test_build_arc_prompt_includes_captions_and_no_invention():
    from app.ai.arc import build_arc_prompt, NO_INVENTION
    p = build_arc_prompt([("평온", "바다가 파랬다"), ("신남", "유채가 끝없이")])
    assert "바다가 파랬다" in p and "유채가 끝없이" in p
    assert NO_INVENTION in p


def test_generate_arc_none_without_captions():
    from app.ai.arc import generate_arc
    # 글귀가 하나도 없으면 AI 호출 없이 None (지어내지 않는다)
    assert generate_arc([(None, None), ("평온", None)]) is None


def test_emotion_arc_endpoint_stores_and_serves(client, monkeypatch):
    import app.ai.analysis as analysis, app.ai.arc as arc_mod
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    monkeypatch.setattr(arc_mod, "generate_arc", lambda moments: "잔잔하게 시작해 뭉클하게 끝난 여행이었다")
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/photos", files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))])
    r = client.post(f"/api/v1/projects/{pid}/emotion-arc")
    assert r.status_code == 200
    assert "뭉클하게" in r.json()["arc"]
    # 저장되어 getProject에도 실린다
    assert "뭉클하게" in client.get(f"/api/v1/projects/{pid}").json()["emotion_arc"]
