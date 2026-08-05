"""사진과 음성을 올리고 순간을 고치거나 정렬한다.
main.py가 라우터로 등록한다.
imaging과 ai 모듈을 부른다."""
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db, get_or_404
from app.models import Photo, Project
from app.imaging import save_resized, small_path
from app.routers.projects import get_project_or_404
from app.schemas import PhotoOut
import app.ai.analysis as analysis
import app.ai.caption as caption

router = APIRouter(prefix="/api/v1", tags=["photos"])


class MomentPatch(BaseModel):
    emotion: str | None = None
    note: str | None = None
    caption: str | None = None


class OrderBody(BaseModel):
    photo_ids: list[str]


@router.post("/projects/{project_id}/photos", status_code=202)
def upload_photos(
    project_id: str,
    files: list[UploadFile],
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = get_project_or_404(db, project_id)
    base = Path(get_settings().data_dir) / "photos" / project.id
    created = []
    start = len(project.photos)
    for i, f in enumerate(files):
        photo = Photo(project_id=project.id, sort_order=start + i, file_path="")
        db.add(photo); db.flush()
        raw = f.file.read()
        # 인쇄에는 원본 해상도가 필요하고 AI 분석에는 1100px이면 충분하다.
        # 리사이즈본만 남기면 실물 책의 화질이 깨진다.
        orig = base / f"{photo.id}.jpg"
        orig.parent.mkdir(parents=True, exist_ok=True)
        orig.write_bytes(raw)
        photo.taken_at = save_resized(raw, base / f"{photo.id}_small.jpg")
        photo.file_path = str(orig)
        created.append(photo)
    # 촬영일이 전부 있으면 그 순서로 정렬하고, 없으면 업로드 순서를 유지한다
    if all(p.taken_at for p in created) and start == 0:
        for i, p in enumerate(sorted(created, key=lambda p: p.taken_at)):
            p.sort_order = i
    db.commit()
    # BackgroundTasks는 순차 실행이라 장당 태스크로 걸면 비전 호출이 직렬화된다
    background.add_task(analysis.analyze_batch, [p.id for p in created])
    ordered = sorted(created, key=lambda p: p.sort_order)
    return {"photos": [PhotoOut.model_validate(p).model_dump() for p in ordered]}


@router.get("/projects/{project_id}/photos/analysis")
def analysis_status(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    return {"photos": [
        {"id": p.id, "analysis_status": p.analysis_status,
         "suggested_emotion": p.suggested_emotion, "caption": p.caption, "transcript": p.transcript}
        for p in project.photos
    ]}


@router.get("/photos/{photo_id}/image")
def photo_image(photo_id: str, db: Session = Depends(get_db)):
    """화면에 쓰는 이미지. 원본은 인쇄용이라 무거우므로 리사이즈본을 먼저 준다."""
    photo = get_or_404(db, Photo, photo_id, "photo")
    path = small_path(photo.file_path)
    if not os.path.exists(path):  # 디스크에서 사라진 파일은 500이 아니라 404로 알린다
        raise HTTPException(404, "image not found")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/moments/{photo_id}/audio", status_code=202)
def upload_audio(photo_id: str, file: UploadFile, background: BackgroundTasks, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    base = Path(get_settings().data_dir) / "audio" / photo.project_id
    base.mkdir(parents=True, exist_ok=True)
    # Whisper가 파일명 확장자로 포맷을 판별하므로 업로드된 확장자를 그대로 보존한다
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".webm", ".m4a", ".mp4", ".ogg", ".wav", ".mp3"):
        ext = ".m4a"
    dest = base / f"{photo.id}{ext}"
    dest.write_bytes(file.file.read())
    # 재녹음이 다른 컨테이너로 오면 이전 파일이 고아로 남으므로 경로가 바뀔 때 지운다
    if photo.audio_path and photo.audio_path != str(dest) and os.path.exists(photo.audio_path):
        try:
            os.remove(photo.audio_path)
        except OSError:
            pass
    photo.audio_path = str(dest)
    db.commit()
    background.add_task(caption.transcribe_and_caption, photo.id)
    return {"id": photo.id, "transcript_pending": True}


def _audio_media_type(path: str) -> str:
    with open(path, "rb") as f:
        head = f.read(12)
    if head[:4] == b"\x1a\x45\xdf\xa3":   # EBML 헤더는 webm
        return "audio/webm"
    if head[4:8] == b"ftyp":              # ISO 베이스 미디어는 m4a와 mp4
        return "audio/mp4"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":  # WAV 헤더
        return "audio/wav"
    if head[:4] == b"OggS":               # Ogg 컨테이너
        return "audio/ogg"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):  # MP3 프레임
        return "audio/mpeg"
    return "application/octet-stream"


@router.get("/moments/{photo_id}")
def get_moment(photo_id: str, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    project = db.get(Project, photo.project_id)
    return {
        "id": photo.id, "caption": photo.caption, "transcript": photo.transcript,
        "emotion": photo.emotion, "project_title": project.title if project else "",
        "has_audio": bool(photo.audio_path),
    }


@router.get("/moments/{photo_id}/audio")
def moment_audio(photo_id: str, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    if not photo.audio_path or not os.path.exists(photo.audio_path):
        raise HTTPException(404, "no audio")
    return FileResponse(photo.audio_path, media_type=_audio_media_type(photo.audio_path))


@router.delete("/moments/{photo_id}")
def delete_moment(photo_id: str, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    paths = [photo.file_path, (photo.file_path or "").replace(".jpg", "_small.jpg"), photo.audio_path]
    db.delete(photo); db.commit()
    for pth in paths:  # 원본과 리사이즈본, 음성 파일도 함께 지운다
        if pth and os.path.exists(pth):
            try:
                os.remove(pth)
            except OSError:
                pass
    return {"ok": True}


@router.patch("/moments/{photo_id}")
def patch_moment(photo_id: str, body: MomentPatch, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(photo, k, v)
    db.commit()
    return {"ok": True}


@router.patch("/projects/{project_id}/photos/order")
def reorder(project_id: str, body: OrderBody, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    by_id = {p.id: p for p in project.photos}
    # 개수까지 봐야 한다. 중복이 섞인 목록은 집합 비교만으로는 걸러지지 않는다.
    if len(body.photo_ids) != len(by_id) or set(body.photo_ids) != set(by_id):
        raise HTTPException(422, "photo_ids must contain exactly all photos")
    for i, pid in enumerate(body.photo_ids):
        by_id[pid].sort_order = i
    db.commit()
    return {"ok": True}
