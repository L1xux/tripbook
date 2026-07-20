"""프로젝트 생성/조회 API 테스트. / pytest가 호출. / FastAPI 클라이언트 사용."""


def test_create_and_get_project(client):
    res = client.post("/api/v1/projects", json={"title": "제주", "mood": "comedy"})
    assert res.status_code == 201
    pid = res.json()["id"]
    got = client.get(f"/api/v1/projects/{pid}").json()
    assert got["title"] == "제주" and got["status"] == "draft"
    assert got["photos"] == [] and got["pages"] == []


def test_invalid_mood_rejected(client):
    res = client.post("/api/v1/projects", json={"title": "x", "mood": "horror"})
    assert res.status_code == 422


def test_get_missing_project_404(client):
    assert client.get("/api/v1/projects/nope").status_code == 404
