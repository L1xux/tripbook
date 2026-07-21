"""페이지 수정/재생성 라우터. / main.py가 등록. / ai.regen 호출."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db, get_or_404
from app.models import Page, Project
from app.ai.regen import regenerate_page_text

router = APIRouter(prefix="/api/v1", tags=["pages"])


class TextBody(BaseModel):
    text: str


class FeedbackBody(BaseModel):
    feedback: str


def _get_page(db: Session, page_id: str) -> Page:
    return get_or_404(db, Page, page_id, "page")


@router.patch("/pages/{page_id}")
def patch_page(page_id: str, body: TextBody, db: Session = Depends(get_db)):
    page = _get_page(db, page_id)
    page.text = body.text
    db.commit()
    return {"id": page.id, "text": page.text}


@router.post("/pages/{page_id}/regenerate")
def regenerate(page_id: str, body: FeedbackBody, db: Session = Depends(get_db)):
    page = _get_page(db, page_id)
    project = db.get(Project, page.project_id)
    siblings = {p.page_number: p for p in project.pages}
    prev_text = getattr(siblings.get(page.page_number - 1), "text", None)
    next_text = getattr(siblings.get(page.page_number + 1), "text", None)
    page.text = regenerate_page_text(project, page, prev_text, next_text, body.feedback)
    page.regen_count += 1
    db.commit()
    return {"id": page.id, "text": page.text, "regen_count": page.regen_count}
