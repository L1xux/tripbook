import asyncio


def test_run_writing_saves_pages_and_sets_ready(client, monkeypatch):
    import app.ai.writer as writer
    import app.db as db_module
    from app.models import Project, Photo

    db = db_module.SessionLocal()
    p = Project(title="t", mood="comedy"); db.add(p); db.commit()
    ph = Photo(project_id=p.id, sort_order=0, file_path="x.jpg", note="바다")
    db.add(ph); db.commit()

    body = "본" * 300

    async def fake_stream(system, user):
        yield f"<<<PAGE photo=none>>>\n{body}\n<<<PAGE photo={ph.id}>>>\n"
        yield body
    monkeypatch.setattr(writer, "stream_book_text", fake_stream)

    asyncio.run(writer.run_writing(p.id))
    db.refresh(p)
    assert p.status == "ready"
    assert [pg.photo_id for pg in p.pages] == [None, ph.id]


def test_run_writing_validation_failure_retries_once_then_errors(client, monkeypatch):
    import app.ai.writer as writer
    import app.db as db_module
    from app.models import Project, Photo
    db = db_module.SessionLocal()
    p = Project(title="t", mood="comedy"); db.add(p); db.commit()
    ph = Photo(project_id=p.id, sort_order=0, file_path="x.jpg"); db.add(ph); db.commit()

    calls = []

    async def bad_stream(system, user):
        calls.append(1)
        yield "<<<PAGE photo=none>>>\n너무 짧은 글"  # 사진 페이지 누락 + 길이 위반
    monkeypatch.setattr(writer, "stream_book_text", bad_stream)
    asyncio.run(writer.run_writing(p.id))
    db.refresh(p)
    assert len(calls) == 2          # 1회 재시도
    assert p.status == "draft"      # 실패하면 draft로 복귀
