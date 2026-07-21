def test_analyze_suggests_emotion(client, monkeypatch, tmp_path):
    import app.ai.analysis as analysis
    import app.db as db_module
    from app.models import Project, Photo
    from PIL import Image

    db = db_module.SessionLocal()
    p = Project(title="t"); db.add(p); db.commit()
    img = tmp_path / "a.jpg"; Image.new("RGB", (10, 10)).save(img)
    m = Photo(project_id=p.id, sort_order=0, file_path=str(img)); db.add(m); db.commit()

    monkeypatch.setattr(analysis, "analyze_image", lambda path: {
        "scene": "노을 지는 해변", "suggested_emotion": "뭉클"})
    analysis.analyze_and_save(m.id)
    db.refresh(m)
    assert m.suggested_emotion == "뭉클"
    assert "노을" in m.ai_scene_description
