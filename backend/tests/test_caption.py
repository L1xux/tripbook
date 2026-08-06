from app.ai.caption import build_caption_prompt


def test_prompt_carries_transcript_and_no_invention_rule():
    p = build_caption_prompt("어 바다가 진짜 파랬어")
    assert "어 바다가 진짜 파랬어" in p
    assert "추가하지 않는다" in p  # 창작 금지 불변식이 프롬프트에 명시됨


def test_transcribe_and_caption_saves(client, monkeypatch):
    import app.ai.caption as caption
    import app.db as db_module
    from app.models import Project, Photo

    db = db_module.SessionLocal()
    p = Project(title="t"); db.add(p); db.commit()
    m = Photo(project_id=p.id, sort_order=0, file_path="x.jpg", audio_path="v.m4a")
    db.add(m); db.commit()

    monkeypatch.setattr(caption, "transcribe", lambda path: "어 바다가 진짜 파랬어 한참 서 있었어")
    monkeypatch.setattr(caption, "polish_caption", lambda t: "바다가 진짜 파랬다. 한참을 서 있었어.")
    caption.transcribe_and_caption(m.id)
    db.refresh(m)
    assert m.transcript.startswith("어 바다가")
    assert m.caption == "바다가 진짜 파랬다. 한참을 서 있었어."
    assert m.analysis_status == "done"


def test_empty_transcript_never_invents_caption(client, monkeypatch):
    """전사가 비면(무음 등) 캡션을 지어내지 않는다 — polish도 호출하지 않는다(창작 금지)."""
    import app.ai.caption as caption
    import app.db as db_module
    from app.models import Project, Photo
    db = db_module.SessionLocal()
    p = Project(title="t"); db.add(p); db.commit()
    m = Photo(project_id=p.id, sort_order=0, file_path="x.jpg", audio_path="v.webm"); db.add(m); db.commit()

    monkeypatch.setattr(caption, "transcribe", lambda path: "")
    called = []
    monkeypatch.setattr(caption, "polish_caption", lambda t: called.append(t) or "지어낸 여행 문장")
    caption.transcribe_and_caption(m.id)
    db.refresh(m)
    assert called == []           # 폴리싱을 아예 부르지 않았다
    assert m.caption is None       # 캡션은 비어 있다
    assert m.analysis_status == "done"


def test_empty_polish_falls_back_to_transcript(client, monkeypatch):
    """편집 LLM이 빈 문자열을 돌려줘도 침묵하지 않는다 — 전사 원문을 캡션으로 보존."""
    import app.ai.caption as caption
    import app.db as db_module
    from app.models import Project, Photo
    db = db_module.SessionLocal()
    p = Project(title="t"); db.add(p); db.commit()
    m = Photo(project_id=p.id, sort_order=0, file_path="x.jpg", audio_path="v.m4a"); db.add(m); db.commit()

    monkeypatch.setattr(caption, "transcribe", lambda path: "바다가 파랬어")
    monkeypatch.setattr(caption, "polish_caption", lambda t: "")
    caption.transcribe_and_caption(m.id)
    db.refresh(m)
    assert m.caption == "바다가 파랬어"
    assert m.analysis_status == "done"


def test_pipeline_failure_keeps_transcript_as_caption(client, monkeypatch):
    import app.ai.caption as caption
    import app.db as db_module
    from app.models import Project, Photo
    db = db_module.SessionLocal()
    p = Project(title="t"); db.add(p); db.commit()
    m = Photo(project_id=p.id, sort_order=0, file_path="x.jpg", audio_path="v.m4a"); db.add(m); db.commit()

    monkeypatch.setattr(caption, "transcribe", lambda path: "바다가 파랬어")
    def boom(t): raise RuntimeError("api down")
    monkeypatch.setattr(caption, "polish_caption", boom)
    caption.transcribe_and_caption(m.id)
    db.refresh(m)
    # 정리 실패해도 전사 원문을 캡션으로 보존한다(보존 우선)
    assert m.caption == "바다가 파랬어"
