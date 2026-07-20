def _ready_project(client):
    import app.db as db_module
    from app.models import Project, Page
    db = db_module.SessionLocal()
    p = Project(title="t", mood="comedy", status="ready"); db.add(p); db.commit()
    pg = Page(project_id=p.id, page_number=1, photo_id=None, text="원본", ai_text="원본")
    db.add(pg); db.commit()
    return p.id, pg.id


def test_patch_page_text(client):
    _, page_id = _ready_project(client)
    res = client.patch(f"/api/v1/pages/{page_id}", json={"text": "수정본"})
    assert res.status_code == 200 and res.json()["text"] == "수정본"


def test_regenerate_uses_feedback(client, monkeypatch):
    import app.routers.pages as pages_router
    _, page_id = _ready_project(client)
    monkeypatch.setattr(pages_router, "regenerate_page_text",
                        lambda project, page, prev_text, next_text, feedback: f"재생성:{feedback}")
    res = client.post(f"/api/v1/pages/{page_id}/regenerate", json={"feedback": "더 웃기게"})
    assert res.json()["text"] == "재생성:더 웃기게"
    assert res.json()["regen_count"] == 1
