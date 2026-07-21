"""프로젝트 생성/조회 라우터. / main.py가 등록. / models·schemas 사용."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db, get_or_404
from app.models import Project
from app.schemas import ProjectCreate, ProjectOut

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
