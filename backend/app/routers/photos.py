"""사진 업로드/수정/정렬 라우터. / main.py가 등록. / imaging, ai.analysis 호출."""
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db
from app.models import Photo
from app.imaging import save_resized
from app.routers.projects import get_project_or_404
from app.schemas import PhotoOut
import app.ai.analysis as analysis

router = APIRouter(prefix="/api/v1", tags=["photos"])


class PhotoPatch(BaseModel):
    note: str | None = None
    emotion: str | None = None
    user_scene_correction: str | None = None


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
    for p in created:
        background.add_task(analysis.analyze_and_save, p.id)
    ordered = sorted(created, key=lambda p: p.sort_order)
    return {"photos": [PhotoOut.model_validate(p).model_dump() for p in ordered]}


@router.get("/projects/{project_id}/photos/analysis")
def analysis_status(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    return {"photos": [
        {"id": p.id, "analysis_status": p.analysis_status, "ai_scene_description": p.ai_scene_description}
        for p in project.photos
    ]}


@router.patch("/photos/{photo_id}")
def patch_photo(photo_id: str, body: PhotoPatch, db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(404, "photo not found")
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
