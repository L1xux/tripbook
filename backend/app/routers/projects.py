"""여행을 만들고 조회하고 지운다.
main.py가 라우터로 등록한다.
models와 schemas, 감정 아크 모듈을 쓴다."""
import os
import shutil
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db, get_or_404
from app.models import Project
from app.schemas import ProjectCreate, ProjectOut
import app.ai.arc as arc_mod

router = APIRouter(prefix="/api/v1", tags=["projects"])


def get_project_or_404(db: Session, project_id: str) -> Project:
    return get_or_404(db, Project, project_id, "project")


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**body.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "title": p.title, "status": p.status}


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return get_project_or_404(db, project_id)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    db.delete(project); db.commit()  # 순간과 수령인은 함께 지워진다
    base = get_settings().data_dir  # 사진과 음성 파일도 지운다
    for sub in ("photos", "audio"):
        shutil.rmtree(os.path.join(base, sub, project_id), ignore_errors=True)
    return {"ok": True}


@router.post("/projects/{project_id}/emotion-arc")
def make_emotion_arc(project_id: str, db: Session = Depends(get_db)):
    """사용자 글귀로 여행 감정 아크를 만들어 저장한다.
    글귀가 없거나 생성에 실패하면 지어내지 않고 기존 값을 그대로 둔다."""
    project = get_project_or_404(db, project_id)
    moments = [(p.emotion, p.caption) for p in project.photos]
    try:
        arc = arc_mod.generate_arc(moments)
    except Exception:
        arc = None
    if arc:
        project.emotion_arc = arc
        db.commit()
    return {"arc": project.emotion_arc}
