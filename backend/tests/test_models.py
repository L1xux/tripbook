from app.models import Project, Photo, Page
import app.db as db_module


def test_create_project_with_photo_and_page(client):
    db = db_module.SessionLocal()
    p = Project(title="제주 여행", mood="family_essay")
    db.add(p); db.commit()
    ph = Photo(project_id=p.id, sort_order=0, file_path="x.jpg", emotion="행복", note="바다")
    db.add(ph); db.commit()
    pg = Page(project_id=p.id, page_number=1, photo_id=ph.id, text="글", ai_text="글")
    db.add(pg); db.commit()
    assert p.status == "draft"
    assert ph.analysis_status == "pending"
    assert len(p.photos) == 1 and len(p.pages) == 1
