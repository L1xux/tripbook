def test_create_and_get_project(client):
    res = client.post("/api/v1/projects", json={"title": "제주"})
    assert res.status_code == 201
    pid = res.json()["id"]
    got = client.get(f"/api/v1/projects/{pid}").json()
    assert got["title"] == "제주" and got["status"] == "draft"
    assert got["reveal_mode"] == "slide"
    assert got["photos"] == [] and got["recipients"] == []


def test_get_missing_project_404(client):
    assert client.get("/api/v1/projects/nope").status_code == 404
