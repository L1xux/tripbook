"""사진 업로드/수정/정렬 라우터. / main.py가 등록. / imaging, ai.analysis 호출."""
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
        # 왜 원본과 분석본을 분리하는가: 인쇄는 원본급 해상도(300dpi)가 필요하고,
        # AI 분석은 1100px이면 충분 — 리사이즈본만 남기면 실물 책 화질이 깨진다
        orig = base / f"{photo.id}.jpg"
        orig.parent.mkdir(parents=True, exist_ok=True)
        orig.write_bytes(raw)
        photo.taken_at = save_resized(raw, base / f"{photo.id}_small.jpg")
        photo.file_path = str(orig)
        created.append(photo)
    # EXIF 촬영일이 전부 있으면 그 순서로 초기 정렬 (없으면 업로드 순서 유지)
    if all(p.taken_at for p in created) and start == 0:
        for i, p in enumerate(sorted(created, key=lambda p: p.taken_at)):
            p.sort_order = i
    db.commit()
    # 왜 배치 하나로 거는가: BackgroundTasks는 순차 실행이라 장당 태스크는 비전 호출을 직렬화한다
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
    """UI 썸네일용 이미지. 리사이즈본을 우선 서빙한다(원본은 인쇄용이라 무거움)."""
    photo = get_or_404(db, Photo, photo_id, "photo")
    return FileResponse(small_path(photo.file_path), media_type="image/jpeg")


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


def _audio_media_type(path: str) -> str:
    with open(path, "rb") as f:
        head = f.read(12)
    if head[:4] == b"\x1a\x45\xdf\xa3":   # EBML → webm/matroska
        return "audio/webm"
    if head[4:8] == b"ftyp":              # ISO-BMFF → m4a/mp4
        return "audio/mp4"
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
    if set(body.photo_ids) != set(by_id):
        raise HTTPException(422, "photo_ids must contain exactly all photos")
    for i, pid in enumerate(body.photo_ids):
        by_id[pid].sort_order = i
    db.commit()
    return {"ok": True}
