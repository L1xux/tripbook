from tests.test_audio import _seed_photo

def test_public_moment_shape(client, monkeypatch):
    mid = _seed_photo(client, monkeypatch)
    client.patch(f"/api/v1/moments/{mid}", json={"caption": "바다가 파랬다", "emotion": "평온"})
    r = client.get(f"/api/v1/moments/{mid}")
    assert r.status_code == 200
    b = r.json()
    assert b["caption"] == "바다가 파랬다"
    assert b["emotion"] == "평온"
    assert b["project_title"] == "제주"
    assert b["has_audio"] is False

def test_public_moment_404(client):
    assert client.get("/api/v1/moments/nope").status_code == 404
