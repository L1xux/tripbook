# Tripbook v2 백엔드 (Voice Photobook) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 "AI 여행기 집필" 백엔드를 "목소리 캡션 포토북" 백엔드로 전환한다 — 사진마다 음성을 Whisper로 전사하고 Claude로 말투 그대로 캡션 정리(창작 금지), 선물·다인수 주문으로 Sweetbook 인쇄.

**Architecture:** FastAPI(SQLite)는 유지. 집필 스택(writer/parser/validator/prompts/regen/events/writing·pages 라우터)을 제거하고, 음성 업로드 → OpenAI Whisper 전사 → Claude Haiku 충실한 캡션 편집 파이프라인과, Recipient 기반 다인수 Sweetbook 주문을 추가한다. Sweetbook client/renderer, config, db, imaging, 프로젝트/사진 업로드는 재사용.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite, anthropic(Haiku 4.5), openai(Whisper), httpx, Pillow, pytest.

**Spec:** `docs/superpowers/specs/2026-07-21-tripbook-voice-photobook-design.md`

## Global Constraints

- 모델: 캡션 정리 `claude-haiku-4-5`(기존 `app/ai/llm.py:ANALYSIS_MODEL` 재사용), 음성 전사 OpenAI `whisper-1`. budget_tokens/temperature 사용 금지.
- API 키는 `.env`로만: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SWEETBOOK_API_KEY`, `SWEETBOOK_ENV`. 리포엔 `.env.example`만.
- **캡션 불변식(창작 금지):** 캡션 정리는 transcript에 없는 사실·감정·인물·장소를 추가하지 않는다. 말투·1인칭 유지, 40~120자, 은유·소설체 금지. 이 규칙은 프롬프트 문자열과 테스트로 강제한다.
- 모든 주요 모듈 상단 3줄 docstring(한국어): "이 파일이 하는 일 / 누가 호출하는가 / 무엇을 호출하는가". 새 파일은 `docs/CODE_TOUR.md`에 1줄 추가.
- 테스트는 LLM/STT/Sweetbook을 전부 monkeypatch/MockTransport로 모킹한다(실키 불필요). 테스트 명령: `cd backend; python -m pytest tests/ -v`.
- 커밋은 태스크마다 최소 1회, conventional commits(`feat:`/`refactor:`/`docs:`).
- 상태 문자열: Project.status ∈ `draft | ordered`. Photo(Moment).analysis_status ∈ `pending | done | failed`.

---

### Task 1: 데이터 모델 v2 (Project/Moment/Recipient) + 스키마

무드·집필 페이지 개념을 제거하고 음성·캡션·수령인 개념을 추가한다.

**Files:**
- Modify: `backend/app/models.py` (전체 교체), `backend/app/schemas.py` (전체 교체)
- Modify: `backend/tests/test_models.py` (전체 교체), `backend/tests/test_projects.py` (전체 교체)

**Interfaces:**
- Produces:
  - `Project(id, title, start_date, end_date, companions, cover_line, reveal_mode, status, sweetbook_book_id, sweetbook_order_id, order_status, photos: list[Photo], recipients: list[Recipient])`
  - `Photo(id, project_id, sort_order, file_path, taken_at, emotion, note, audio_path, transcript, caption, ai_scene_description, suggested_emotion, analysis_status)`
  - `Recipient(id, project_id, name, phone, address, gift_message, sweetbook_order_id, order_status)`
  - `ProjectCreate`, `MomentOut`, `RecipientOut`, `ProjectOut`

- [ ] **Step 1: 실패하는 테스트** — `backend/tests/test_models.py` 전체 교체:
```python
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
```

- [ ] **Step 2: 실행해 실패 확인** — `python -m pytest tests/test_models.py -v` → FAIL (Recipient 없음 / mood 인자 제거됨)

- [ ] **Step 3: 구현** — `backend/app/models.py` 전체 교체:
```python
"""DB 테이블 정의(Project/Photo=순간/Recipient). / 라우터와 AI 파이프라인이 호출. / db.Base를 사용."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


def _uid() -> str:
    return uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    title: Mapped[str] = mapped_column(String)
    start_date: Mapped[str | None] = mapped_column(String, nullable=True)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    companions: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_line: Mapped[str | None] = mapped_column(String, nullable=True)  # 표지 문구
    reveal_mode: Mapped[str] = mapped_column(String, default="slide")  # slide | dim (설계 3.5 A/B)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | ordered
    sweetbook_book_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sweetbook_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_status: Mapped[str | None] = mapped_column(String, nullable=True)
    photos: Mapped[list["Photo"]] = relationship(order_by="Photo.sort_order", cascade="all, delete-orphan")
    recipients: Mapped[list["Recipient"]] = relationship(cascade="all, delete-orphan")


class Photo(Base):
    """한 '순간' — 사진 + 음성 + 캡션 + 감정."""
    __tablename__ = "photos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    emotion: Mapped[str | None] = mapped_column(String, nullable=True)  # 사용자가 고른 감정 태그
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)  # 원본 음성
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)  # Whisper 전사 원문
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI 정리본(사용자 수정 가능)
    ai_scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)  # 감정 제안 근거(내부)
    suggested_emotion: Mapped[str | None] = mapped_column(String, nullable=True)  # AI가 제안한 감정
    analysis_status: Mapped[str] = mapped_column(String, default="pending")


class Recipient(Base):
    """선물 수령인 — 주문 시 1명당 인쇄 1권."""
    __tablename__ = "recipients"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, default="")
    gift_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sweetbook_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_status: Mapped[str | None] = mapped_column(String, nullable=True)
```

- [ ] **Step 4: 스키마 교체** — `backend/app/schemas.py` 전체 교체:
```python
"""요청/응답 Pydantic 스키마. / 라우터가 호출. / models와 필드가 대응."""
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    start_date: str | None = None
    end_date: str | None = None
    companions: str | None = None
    cover_line: str | None = None


class MomentOut(BaseModel):
    id: str
    sort_order: int
    emotion: str | None
    note: str | None
    caption: str | None
    transcript: str | None
    suggested_emotion: str | None
    analysis_status: str
    model_config = {"from_attributes": True}


class RecipientOut(BaseModel):
    id: str
    name: str
    phone: str | None
    address: str
    gift_message: str | None
    order_status: str | None
    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: str
    title: str
    status: str
    cover_line: str | None
    reveal_mode: str
    start_date: str | None
    end_date: str | None
    companions: str | None
    order_status: str | None
    photos: list[MomentOut]
    recipients: list[RecipientOut]
    model_config = {"from_attributes": True}
```

- [ ] **Step 5: 프로젝트 라우터/테스트 업데이트** — `backend/app/routers/projects.py`에서 `create_project` 반환을 mood 없이 조정. 해당 함수 교체:
```python
@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**body.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "title": p.title, "status": p.status}
```
그리고 `backend/tests/test_projects.py` 전체 교체:
```python
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
```

- [ ] **Step 6: 통과 확인** — `python -m pytest tests/test_models.py tests/test_projects.py -v` → PASS

- [ ] **Step 7: 커밋** — `git add -A; git commit -m "refactor: v2 data model (Project/Moment/Recipient), drop mood/pages"` (CODE_TOUR.md는 Task 7에서 일괄 갱신)

---

### Task 2: 집필 스택 제거

목소리 캡션 제품에는 소설 집필기가 필요 없다. 관련 모듈·라우터·테스트를 제거한다.

**Files:**
- Delete: `backend/app/ai/writer.py`, `backend/app/ai/parser.py`, `backend/app/ai/validator.py`, `backend/app/ai/prompts.py`, `backend/app/ai/regen.py`, `backend/app/events.py`, `backend/app/routers/writing.py`, `backend/app/routers/pages.py`
- Delete: `backend/tests/test_writing.py`, `backend/tests/test_parser.py`, `backend/tests/test_validator.py`, `backend/tests/test_prompts.py`, `backend/tests/test_pages.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 파일 삭제** — 위 Delete 목록 전부 제거:
```bash
cd backend
rm app/ai/writer.py app/ai/parser.py app/ai/validator.py app/ai/prompts.py app/ai/regen.py app/events.py
rm app/routers/writing.py app/routers/pages.py
rm tests/test_writing.py tests/test_parser.py tests/test_validator.py tests/test_prompts.py tests/test_pages.py
```

- [ ] **Step 2: main.py에서 라우터 등록 제거** — `backend/app/main.py`의 `create_app()` 내부 라우터 블록을 교체:
```python
    from app.routers import projects, photos, orders
    app.include_router(projects.router)
    app.include_router(photos.router)
    app.include_router(orders.router)
```

- [ ] **Step 3: 실행해 확인** — `python -m pytest tests/ -v`
  - 예상: `test_models`, `test_projects`, `test_sweetbook` 통과. `test_photos`, `test_analysis`, `test_orders`는 아직 구버전 참조로 실패할 수 있음(다음 태스크에서 교체). 삭제한 모듈 import 에러가 없어야 한다.
  - 확인 포인트: `python -c "from app.main import create_app; create_app()"` 가 예외 없이 실행.

- [ ] **Step 4: 커밋** — `git add -A; git commit -m "refactor: remove story-generation stack (writer/parser/validator/prompts/regen/events)"`

---

### Task 3: 음성 업로드 + Whisper 전사 클라이언트

**Files:**
- Modify: `backend/app/config.py` (openai_api_key 추가), `backend/requirements.txt`
- Create: `backend/app/ai/stt.py`, `backend/tests/test_stt.py`
- Modify: `backend/app/routers/photos.py` (음성 업로드 엔드포인트 추가), `.env.example`

**Interfaces:**
- Produces: `transcribe(audio_path: str) -> str` (Whisper), `get_stt_client()`(monkeypatch 대상). `POST /api/v1/moments/{photo_id}/audio` (multipart `file`) → 202 `{id, transcript_pending: true}` — 저장 후 백그라운드로 전사+캡션 시작(캡션은 Task 4).

- [ ] **Step 1: 설정/의존성** — `backend/app/config.py`의 Settings에 필드 추가(anthropic_api_key 아래):
```python
    openai_api_key: str = ""
```
`backend/requirements.txt` 끝에 추가:
```
openai>=1.0
```
`.env.example` 전체 교체:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
SWEETBOOK_API_KEY=sb-...
SWEETBOOK_ENV=sandbox
```

- [ ] **Step 2: 실패하는 테스트** — `backend/tests/test_stt.py`:
```python
def test_upload_audio_saves_and_starts_pipeline(client, monkeypatch, tmp_path):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    import app.ai.caption as caption
    calls = []
    monkeypatch.setattr(caption, "transcribe_and_caption", lambda pid: calls.append(pid))

    pid = client.post("/api/v1/projects", json={"title": "t"}).json()["id"]
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    photo = client.post(f"/api/v1/projects/{pid}/photos",
                        files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))]).json()["photos"][0]

    res = client.post(f"/api/v1/moments/{photo['id']}/audio",
                      files=[("file", ("v.m4a", b"FAKEAUDIO", "audio/m4a"))])
    assert res.status_code == 202
    assert calls == [photo["id"]]  # 캡션 파이프라인이 이 순간으로 시작됨


def test_transcribe_calls_whisper(monkeypatch, tmp_path):
    import app.ai.stt as stt

    class FakeAudio:
        def create(self, **kw):
            class R: text = "어 바다가 진짜 파랬어"
            return R()
    class FakeClient:
        audio = type("A", (), {"transcriptions": FakeAudio()})()
    monkeypatch.setattr(stt, "get_stt_client", lambda: FakeClient())
    f = tmp_path / "v.m4a"; f.write_bytes(b"x")
    assert stt.transcribe(str(f)) == "어 바다가 진짜 파랬어"
```

- [ ] **Step 3: 실행해 실패 확인** — FAIL (`app.ai.stt` 없음)

- [ ] **Step 4: STT 구현** — `backend/app/ai/stt.py`:
```python
"""음성 전사(OpenAI Whisper). / caption 파이프라인이 호출. / openai SDK 사용."""
from functools import lru_cache
import openai
from app.config import get_settings


@lru_cache
def get_stt_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=get_settings().openai_api_key or None)


def transcribe(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        res = get_stt_client().audio.transcriptions.create(model="whisper-1", file=f)
    return res.text.strip()
```

- [ ] **Step 5a: 캡션 모듈 스텁 생성** — Task 4에서 전체 구현하지만, 이 태스크의 업로드 엔드포인트와 테스트가 `app.ai.caption`을 import/monkeypatch하므로 먼저 스텁을 만든다. `backend/app/ai/caption.py`:
```python
"""음성 캡션 파이프라인(전사→충실한 편집). / 음성 업로드가 백그라운드로 호출. / stt·llm 사용. (Task 4에서 전체 구현)"""


def transcribe_and_caption(photo_id: str) -> None:
    return None
```

- [ ] **Step 5b: 음성 업로드 엔드포인트** — `backend/app/routers/photos.py`에 추가. 상단 import에 `import app.ai.caption as caption` 추가하고(파일 맨 위 import 블록), `photo_image` 함수 아래에 삽입:
```python
@router.post("/moments/{photo_id}/audio", status_code=202)
def upload_audio(photo_id: str, file: UploadFile, background: BackgroundTasks, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    base = Path(get_settings().data_dir) / "audio" / photo.project_id
    base.mkdir(parents=True, exist_ok=True)
    dest = base / f"{photo.id}.m4a"
    dest.write_bytes(file.file.read())
    photo.audio_path = str(dest)
    db.commit()
    background.add_task(caption.transcribe_and_caption, photo.id)
    return {"id": photo.id, "transcript_pending": True}
```

- [ ] **Step 6: 통과 확인** — `python -m pytest tests/test_stt.py -v` → PASS

- [ ] **Step 7: 커밋** — `git add -A; git commit -m "feat: audio upload + Whisper transcription client"`

---

### Task 4: 캡션 파이프라인 (충실한 편집, 창작 금지)

**Files:**
- Modify: `backend/app/ai/caption.py` (Task 3의 스텁을 전체 구현으로 교체)
- Create: `backend/tests/test_caption.py`

**Interfaces:**
- Consumes: `app.ai.stt.transcribe`, `app.ai.llm.get_client`/`first_text`, `Photo`, `SessionLocal`
- Produces: `build_caption_prompt(transcript: str) -> str`, `polish_caption(transcript: str) -> str`, `transcribe_and_caption(photo_id: str) -> None`

- [ ] **Step 1: 실패하는 테스트** — `backend/tests/test_caption.py`:
```python
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
```

- [ ] **Step 2: 실행해 실패 확인** — FAIL (`app.ai.caption` 없음)

- [ ] **Step 3: 구현** — `backend/app/ai/caption.py`:
```python
"""음성 캡션 파이프라인(전사→충실한 편집). / 음성 업로드가 백그라운드로 호출. / stt·llm 사용."""
import app.db as db_module
from app.models import Photo
from app.ai.stt import transcribe
from app.ai.llm import ANALYSIS_MODEL, first_text, get_client

# 왜 별도 상수: 창작 금지 규칙을 프롬프트와 테스트가 같은 문자열로 공유한다
NO_INVENTION = "원문에 없는 사실·감정·인물·장소를 추가하지 않는다"


def build_caption_prompt(transcript: str) -> str:
    return (
        "여행 사진을 보며 사용자가 말한 내용을 그대로 짧은 캡션으로 다듬어라.\n"
        f"규칙: {NO_INVENTION}. 말투와 1인칭 시점을 유지한다. "
        "'음/어' 같은 군더더기와 중복만 정리한다. 40~120자, 1~2문장. "
        "은유·각색·소설체 금지. 캡션 본문만 출력한다.\n\n"
        f"사용자가 말한 것: {transcript}"
    )


def polish_caption(transcript: str) -> str:
    res = get_client().messages.create(
        model=ANALYSIS_MODEL, max_tokens=300,
        messages=[{"role": "user", "content": build_caption_prompt(transcript)}],
    )
    return first_text(res).strip()


def transcribe_and_caption(photo_id: str) -> None:
    with db_module.session_scope() as db:
        photo = db.get(Photo, photo_id)
        if not photo or not photo.audio_path:
            return
        try:
            photo.transcript = transcribe(photo.audio_path)
            try:
                photo.caption = polish_caption(photo.transcript)
            except Exception:
                # 정리 실패 시 전사 원문을 캡션으로 보존 (감정 보존 우선)
                photo.caption = photo.transcript
            photo.analysis_status = "done"
        except Exception:
            photo.analysis_status = "failed"
        db.commit()
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/test_caption.py -v` → PASS

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "feat: faithful caption pipeline (Whisper transcript -> Claude edit, no invention)"`

---

### Task 5: 감정 태그 제안 (Haiku) + 사진/순간 API 정리

기존 사진 분석을 "감정 제안"으로 용도 변경하고, photos 라우터를 v2 필드에 맞춘다.

**Files:**
- Modify: `backend/app/ai/analysis.py` (감정 제안), `backend/app/routers/photos.py` (v2 정리)
- Modify: `backend/tests/test_analysis.py` (전체 교체), `backend/tests/test_photos.py` (전체 교체)

**Interfaces:**
- Produces: `analyze_and_save(photo_id)` — 성공 시 `suggested_emotion`(아래 6종 중 1) + `ai_scene_description` 저장, `analysis_status` 유지(캡션 파이프라인이 최종 done 설정). `EMOTIONS = ["설렘","행복","평온","뭉클","신남","아쉬움"]`. `PATCH /api/v1/moments/{id}` body `{emotion?, note?, caption?}`.

- [ ] **Step 1: 실패하는 테스트** — `backend/tests/test_analysis.py` 전체 교체:
```python
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
```
`backend/tests/test_photos.py` 전체 교체:
```python
import io
from PIL import Image


def _jpg():
    buf = io.BytesIO(); Image.new("RGB", (1200, 900), "red").save(buf, "JPEG"); return buf.getvalue()


def _project(client):
    return client.post("/api/v1/projects", json={"title": "t"}).json()["id"]


def test_upload_creates_moments(client, monkeypatch):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    pid = _project(client)
    res = client.post(f"/api/v1/projects/{pid}/photos",
                      files=[("files", ("a.jpg", _jpg(), "image/jpeg")), ("files", ("b.jpg", _jpg(), "image/jpeg"))])
    assert res.status_code == 202
    assert [m["sort_order"] for m in res.json()["photos"]] == [0, 1]


def test_patch_moment_and_reorder(client, monkeypatch):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    pid = _project(client)
    ms = client.post(f"/api/v1/projects/{pid}/photos",
                     files=[("files", ("a.jpg", _jpg(), "image/jpeg")), ("files", ("b.jpg", _jpg(), "image/jpeg"))]).json()["photos"]
    a, b = ms[0]["id"], ms[1]["id"]
    assert client.patch(f"/api/v1/moments/{a}", json={"emotion": "평온", "caption": "직접 쓴 캡션"}).status_code == 200
    assert client.patch(f"/api/v1/projects/{pid}/photos/order", json={"photo_ids": [b, a]}).status_code == 200
    got = client.get(f"/api/v1/projects/{pid}").json()["photos"]
    assert [m["id"] for m in got] == [b, a]
    assert got[1]["caption"] == "직접 쓴 캡션"
```

- [ ] **Step 2: 실행해 실패 확인** — FAIL (analyze_image 반환 형식/`/moments/{id}` PATCH 없음)

- [ ] **Step 3: analysis.py 감정 제안으로 교체** — `backend/app/ai/analysis.py`의 `ANALYSIS_SCHEMA`, `analyze_image`, `analyze_and_save`를 교체(파일 상단 import·`analyze_batch`는 유지):
```python
EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"]

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "scene": {"type": "string", "description": "사진 장면을 한국어 1문장으로"},
        "suggested_emotion": {"type": "string", "enum": EMOTIONS},
    },
    "required": ["scene", "suggested_emotion"],
    "additionalProperties": False,
}


def analyze_image(image_path: str) -> dict:
    import base64, json
    with open(small_path(image_path), "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    res = get_client().messages.create(
        model=ANALYSIS_MODEL, max_tokens=512,
        output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
            {"type": "text", "text": "이 여행 사진의 장면과 어울리는 감정 하나를 골라줘."},
        ]}],
    )
    return json.loads(first_text(res))


def analyze_and_save(photo_id: str) -> None:
    with db_module.session_scope() as db:
        photo = db.get(Photo, photo_id)
        if not photo:
            return
        try:
            r = analyze_image(photo.file_path)
            photo.ai_scene_description = r["scene"]
            photo.suggested_emotion = r["suggested_emotion"]
        except Exception:
            pass  # 감정 제안은 실패해도 무해 — 사용자가 직접 고를 수 있다
        db.commit()
```
(파일 상단이 `import json`을 이미 안 쓰면 `analyze_image` 내부의 지역 import로 충분하다. `from app.imaging import small_path`, `from app.ai.llm import ANALYSIS_MODEL, first_text, get_client`, `import app.db as db_module`, `from app.models import Photo` import는 유지.)

- [ ] **Step 4: photos.py를 v2로 정리** — `backend/app/routers/photos.py`에서:
  1. `analysis_status`(GET) 응답을 `{"id","analysis_status","suggested_emotion","caption","transcript"}`로 바꾸고,
  2. 기존 `PhotoPatch`를 교체하고 PATCH 경로를 `/moments/{photo_id}`로 바꾼다.

  `PhotoPatch` 교체:
```python
class MomentPatch(BaseModel):
    emotion: str | None = None
    note: str | None = None
    caption: str | None = None
```
  `analysis_status` GET 함수의 리스트 컴프리헨션 교체:
```python
    return {"photos": [
        {"id": p.id, "analysis_status": p.analysis_status,
         "suggested_emotion": p.suggested_emotion, "caption": p.caption, "transcript": p.transcript}
        for p in project.photos
    ]}
```
  `patch_photo` 함수 교체:
```python
@router.patch("/moments/{photo_id}")
def patch_moment(photo_id: str, body: MomentPatch, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(photo, k, v)
    db.commit()
    return {"ok": True}
```

- [ ] **Step 5: 통과 확인** — `python -m pytest tests/test_analysis.py tests/test_photos.py -v` → PASS

- [ ] **Step 6: 커밋** — `git add -A; git commit -m "feat: emotion suggestion via Haiku, moment PATCH (caption/emotion/note)"`

---

### Task 6: 수령인 + 선물·다인수 주문

책을 1회 렌더한 뒤 (나 + 수령인들) 각각에게 인쇄 주문을 생성한다.

**Files:**
- Modify: `backend/app/routers/orders.py` (전체 교체), `backend/tests/test_orders.py` (전체 교체), `backend/app/sweetbook/renderer.py` (payload 함수 2개), `backend/tests/test_sweetbook.py` (가짜 페이지 객체)

**Interfaces:**
- Consumes: `SweetbookClient`, `TemplateRenderer`, `get_project_or_404`, `Recipient`
- Produces:
  - `POST /api/v1/projects/{id}/recipients` body `{name, address, phone?, gift_message?}` → 201 `{id}`
  - `DELETE /api/v1/recipients/{rid}` → `{ok}`
  - `POST /api/v1/projects/{id}/order` body `{spec, shipping}` → 200 `{book_uid, orders: [{to, order_uid}]}` — 책 1회 렌더, 나(shipping)+수령인들에게 각 1권. project.status="ordered". 사진이 없으면 409.
  - `GET /api/v1/projects/{id}/order/status`, webhook은 project와 recipient 양쪽에서 orderUid 매칭.

- [ ] **Step 1: 실패하는 테스트** — `backend/tests/test_orders.py` 전체 교체:
```python
import httpx


def _project_with_photo(client, monkeypatch):
    import app.ai.analysis as analysis
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/photos", files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))])
    return pid


_ORDER_SEQ = iter(["O-me", "O-mom"])


def _mock_client():
    from app.sweetbook.client import SweetbookClient
    def handler(req):
        data = {"bookUid": "B1"}
        if req.url.path.endswith("/orders"):
            data = {"orderUid": next(_ORDER_SEQ)}
        return httpx.Response(200, json={"success": True, "message": "ok", "data": data})
    return SweetbookClient("k", "sandbox", transport=httpx.MockTransport(handler))


def test_gift_order_creates_one_print_per_person(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = _project_with_photo(client, monkeypatch)
    client.post(f"/api/v1/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
    res = client.post(f"/api/v1/projects/{pid}/order",
                      json={"spec": {"bookSpecUid": "S1"}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 200
    body = res.json()
    assert body["book_uid"] == "B1"
    assert len(body["orders"]) == 2  # 나 + 엄마
    assert client.get(f"/api/v1/projects/{pid}/order/status").json()["order_status"] == "ORDERED"


def test_order_requires_photos(client, monkeypatch):
    import app.routers.orders as orders
    monkeypatch.setattr(orders, "get_sweetbook_client", _mock_client)
    pid = client.post("/api/v1/projects", json={"title": "빈 여행"}).json()["id"]
    res = client.post(f"/api/v1/projects/{pid}/order", json={"spec": {}, "shipping": {"name": "나", "address": "부산"}})
    assert res.status_code == 409
```

- [ ] **Step 2: 실행해 실패 확인** — FAIL (recipients 엔드포인트/다인수 주문 없음)

- [ ] **Step 3: 구현** — `backend/app/routers/orders.py` 전체 교체:
```python
"""수령인·주문·웹훅 라우터. / main.py가 등록. / sweetbook 모듈 호출."""
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db, get_or_404
from app.models import Project, Recipient
from app.routers.projects import get_project_or_404
from app.sweetbook.client import SweetbookClient, SweetbookError
from app.sweetbook.renderer import TemplateRenderer

router = APIRouter(prefix="/api/v1", tags=["orders"])


@lru_cache
def get_sweetbook_client() -> SweetbookClient:
    s = get_settings()
    return SweetbookClient(s.sweetbook_api_key, s.sweetbook_env)


class RecipientBody(BaseModel):
    name: str
    address: str
    phone: str | None = None
    gift_message: str | None = None


@router.post("/projects/{project_id}/recipients", status_code=201)
def add_recipient(project_id: str, body: RecipientBody, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    r = Recipient(project_id=project_id, **body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id}


@router.delete("/recipients/{recipient_id}")
def remove_recipient(recipient_id: str, db: Session = Depends(get_db)):
    r = get_or_404(db, Recipient, recipient_id, "recipient")
    db.delete(r); db.commit()
    return {"ok": True}


class OrderBody(BaseModel):
    spec: dict
    shipping: dict


@router.post("/projects/{project_id}/order")
def create_order(project_id: str, body: OrderBody, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    if not project.photos:
        raise HTTPException(409, "순간을 하나 이상 담은 뒤 주문할 수 있습니다")
    client = get_sweetbook_client()
    try:
        # 책은 1회만 렌더 — 같은 책을 여러 권 인쇄한다
        book_uid = TemplateRenderer(client).render(project, project.photos, body.spec)
        orders = []
        # 나에게 1권
        me = client.create_order({"bookUid": book_uid, **body.shipping})
        project.sweetbook_order_id = me.get("orderUid")
        orders.append({"to": body.shipping.get("name", "나"), "order_uid": me.get("orderUid")})
        # 수령인마다 1권
        for r in project.recipients:
            o = client.create_order({"bookUid": book_uid, "name": r.name, "address": r.address,
                                     "phone": r.phone, "giftMessage": r.gift_message})
            r.sweetbook_order_id = o.get("orderUid"); r.order_status = "ORDERED"
            orders.append({"to": r.name, "order_uid": o.get("orderUid")})
    except SweetbookError as e:
        raise HTTPException(502, f"주문에 실패했습니다: {e}")
    project.sweetbook_book_id = book_uid
    project.order_status = "ORDERED"
    project.status = "ordered"
    db.commit()
    return {"book_uid": book_uid, "orders": orders}


@router.get("/projects/{project_id}/order/status")
def order_status(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    return {"order_status": project.order_status,
            "recipients": [{"name": r.name, "order_status": r.order_status} for r in project.recipients]}


class WebhookBody(BaseModel):
    orderUid: str
    status: str


@router.post("/webhooks/sweetbook")
def webhook(body: WebhookBody, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(sweetbook_order_id=body.orderUid).first()
    if project:
        project.order_status = body.status
    r = db.query(Recipient).filter_by(sweetbook_order_id=body.orderUid).first()
    if r:
        r.order_status = body.status
    db.commit()
    return {"ok": True}
```

- [ ] **Step 3b: 렌더러를 순간(caption) 기반으로 갱신** — 렌더러는 삭제된 Page의 `.text`/`.photo_id`를 참조하므로 순간 필드로 바꿔야 한다. `backend/app/sweetbook/renderer.py`의 `build_cover_payload`·`build_content_payload` 교체:
```python
def build_cover_payload(project, spec: dict) -> dict:
    return {"templateUid": spec.get("coverTemplateUid"),
            "params": {"title": project.title, "coverLine": getattr(project, "cover_line", None)}}


def build_content_payload(moment, spec: dict) -> dict:
    # 한 순간 = 한 페이지: 사진 + 캡션(사용자의 말)
    return {"templateUid": spec.get("contentTemplateUid"),
            "params": {"photoId": getattr(moment, "id", None), "caption": getattr(moment, "caption", None) or ""}}
```
  그리고 `backend/tests/test_sweetbook.py`의 `test_renderer_calls_full_sequence`에서:
  - 사용하지 않는 `from app.ai.parser import ParsedPage` 줄을 삭제한다(parser 모듈은 Task 2에서 제거됨 — 이 import가 남아 있으면 test_sweetbook이 ModuleNotFoundError로 깨진다).
  - 가짜 페이지 객체를 순간 형태로 바꾼다:
```python
    pages = [type("Pg", (), {"id": "m1", "photo_id": None, "caption": "글", "page_number": 1})()]
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/ -v` → 전체 PASS

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "feat: recipients + gift multi-copy order, renderer uses moment captions"`

---

### Task 7: 문서 + E2E 데모 갱신

**Files:**
- Modify: `backend/scripts/demo_e2e.py` (전체 교체), `docs/CODE_TOUR.md`, `docs/ARCHITECTURE.md`, `CLAUDE.md`
- Delete: `backend/scripts/hello_book.py` 유지(그대로), 구버전 문서 항목 정리

- [ ] **Step 1: CODE_TOUR.md v2 정리** — 삭제된 파일(writer/parser/validator/prompts/regen/events/writing/pages) 항목 제거, 추가된 파일(`ai/stt.py`, `ai/caption.py`) 항목 추가. 읽는 순서: config→db→models→schemas→routers(projects→photos→orders)→ai(llm→analysis→stt→caption)→sweetbook(client→renderer). 각 1줄 + "여기서 볼 것".

- [ ] **Step 2: ARCHITECTURE.md v2 시나리오 교체** — 3개 여정을 v2로: ① 순간 담기(`Step…Photos` → `photos.py:upload_photos` → 감정제안 `analysis.py`), ② 목소리 캡션(`upload_audio` → `caption.py:transcribe_and_caption` → Whisper→Claude → 폴링), ③ 선물 주문(`orders.py:create_order` → `renderer.py` 1회 렌더 → 나+수령인 N개 `create_order` → webhook). 파일:함수 명시(한국어).

- [ ] **Step 3: CLAUDE.md 갱신** — 모델 줄을 "캡션 `claude-haiku-4-5`, 전사 Whisper `whisper-1`"로, 키에 `OPENAI_API_KEY` 추가, 무드/집필 규칙 제거, 캡션 불변식(창작 금지) 규칙 추가.

- [ ] **Step 4: demo_e2e.py 교체** — `backend/scripts/demo_e2e.py` 전체 교체:
```python
"""E2E 데모(v2): 프로젝트 생성→사진 업로드→음성 업로드(캡션)→수령인→주문.
실행: cd backend; python scripts/demo_e2e.py [--order]
사전조건: uvicorn 실행, .env에 실키."""
import io, sys, time
import httpx
from PIL import Image

BASE = "http://localhost:8000/api/v1"


def jpg(color):
    buf = io.BytesIO(); Image.new("RGB", (1200, 900), color).save(buf, "JPEG"); return buf.getvalue()


def main(order: bool):
    c = httpx.Client(timeout=300)
    pid = c.post(f"{BASE}/projects", json={"title": "제주, 봄", "companions": "엄마"}).json()["id"]
    print("project:", pid)
    photos = c.post(f"{BASE}/projects/{pid}/photos", files=[
        ("files", ("a.jpg", jpg("navy"), "image/jpeg")),
        ("files", ("b.jpg", jpg("orange"), "image/jpeg")),
    ]).json()["photos"]
    for m in photos:
        # 실제 음성 파일이 있으면 그것을 사용. 데모는 짧은 더미 바이트.
        c.post(f"{BASE}/moments/{m['id']}/audio", files=[("file", ("v.m4a", b"DUMMYAUDIO", "audio/m4a"))])
    print("캡션 생성 대기…")
    for _ in range(30):
        st = c.get(f"{BASE}/projects/{pid}/photos/analysis").json()["photos"]
        if all(x["analysis_status"] in ("done", "failed") for x in st):
            break
        time.sleep(2)
    for x in c.get(f"{BASE}/projects/{pid}/photos/analysis").json()["photos"]:
        print("  캡션:", x["caption"])
    if order:
        c.post(f"{BASE}/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
        res = c.post(f"{BASE}/projects/{pid}/order", json={
            "spec": {"bookSpecUid": "REPLACE_ME"},
            "shipping": {"name": "나", "phone": "010-0000-0000", "address": "부산"}})
        print("order:", res.json())
    print("완료:", f"http://localhost:5173/ (프로젝트 {pid})")


if __name__ == "__main__":
    main("--order" in sys.argv)
```

- [ ] **Step 5: 전체 검증** — `python -m pytest tests/ -v` 전체 PASS. `python -c "from app.main import create_app; create_app()"` 예외 없음.

- [ ] **Step 6: 커밋** — `git add -A; git commit -m "docs: v2 code tour, architecture, e2e demo (voice caption + gifting)"`

---

## Self-Review 결과

- **스펙 커버리지:** 데이터 모델 v2(§5, T1), 집필 스택 제거(§4, T2), 음성 업로드+Whisper(§4·§6·§9, T3), 충실한 캡션+불변식(§6, T4), 감정 제안(§6, T5), 선물·다인수 주문(§2·§4, T6), 문서/E2E(§8, T7). 프론트엔드(§3.5·§3.6)와 localStorage 서재는 **Plan B(프론트 v2)**에서 다룬다.
- **디자인/인쇄 레이아웃(A 스타일 캡션):** 렌더러가 사진+캡션을 인쇄에 배치하는 세부는 Sweetbook Sandbox 실응답 확정 후 `build_content_payload`에서 조정(스펙 §9·기존 `SWEETBOOK_API_FEEDBACK.md`와 동일 접근). 코드 파급은 payload 함수에 국소화되어 있음.
- **타입 일관성:** `transcribe_and_caption(photo_id)`, `polish_caption(transcript)`, `analyze_and_save(photo_id)`/`analyze_batch(ids)`, `get_stt_client`/`get_sweetbook_client`(monkeypatch 대상) 명이 소비처와 일치. Photo=순간 필드(audio_path/transcript/caption/suggested_emotion)가 라우터·파이프라인·테스트에서 동일.
- **미확정 외부 의존:** `OPENAI_API_KEY`(Whisper), Sweetbook `bookSpecUid` 등은 실행 시 `.env`/포털 값으로 채운다. `REPLACE_ME`는 실검증 시점에 확정.
