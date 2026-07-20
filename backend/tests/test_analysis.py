import json


def test_analyze_and_save_success(client, monkeypatch, tmp_path):
    import app.ai.analysis as analysis
    import app.db as db_module
    from app.models import Project, Photo

    db = db_module.SessionLocal()
    p = Project(title="t", mood="comedy"); db.add(p); db.commit()
    img = tmp_path / "a.jpg"
    from PIL import Image
    Image.new("RGB", (10, 10)).save(img)
    ph = Photo(project_id=p.id, sort_order=0, file_path=str(img))
    db.add(ph); db.commit()

    monkeypatch.setattr(analysis, "analyze_image", lambda path: {
        "scene": "노을 지는 해변", "location_guess": "해변", "mood": "평화",
        "people": "2명", "notable_details": ["맨발"]})
    analysis.analyze_and_save(ph.id)
    db.refresh(ph)
    assert ph.analysis_status == "done"
    assert "노을 지는 해변" in ph.ai_scene_description


def test_analyze_and_save_failure_marks_failed(client, monkeypatch):
    import app.ai.analysis as analysis
    import app.db as db_module
    from app.models import Project, Photo
    db = db_module.SessionLocal()
    p = Project(title="t", mood="comedy"); db.add(p); db.commit()
    ph = Photo(project_id=p.id, sort_order=0, file_path="missing.jpg")
    db.add(ph); db.commit()

    def boom(path):
        raise RuntimeError("api down")
    monkeypatch.setattr(analysis, "analyze_image", boom)
    analysis.analyze_and_save(ph.id)
    db.refresh(ph)
    assert ph.analysis_status == "failed"
