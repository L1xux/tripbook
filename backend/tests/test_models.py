import app.db as db_module
from app.models import Project, Photo, Recipient


def test_project_moment_recipient(client):
    db = db_module.SessionLocal()
    p = Project(title="제주, 봄")
    db.add(p); db.commit()
    m = Photo(project_id=p.id, sort_order=0, file_path="x.jpg",
             emotion="평온", caption="바다가 파랬다", transcript="어 바다가 진짜 파랬어")
    db.add(m); db.commit()
    r = Recipient(project_id=p.id, name="엄마", address="서울")
    db.add(r); db.commit()
    assert p.status == "draft"
    assert p.reveal_mode == "slide"
    assert m.analysis_status == "pending"
    assert len(p.photos) == 1 and len(p.recipients) == 1
