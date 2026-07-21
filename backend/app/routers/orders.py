"""주문 생성/상태/웹훅 라우터. / main.py가 등록. / sweetbook 모듈 호출."""
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db
from app.models import Project
from app.routers.projects import get_project_or_404
from app.sweetbook.client import SweetbookClient, SweetbookError
from app.sweetbook.renderer import TemplateRenderer

router = APIRouter(prefix="/api/v1", tags=["orders"])


# 왜 캐시하는가: 렌더링은 3+N번의 순차 HTTP 호출 — 요청마다 새 클라이언트를 만들면 커넥션 풀이 버려진다
@lru_cache
def get_sweetbook_client() -> SweetbookClient:
    s = get_settings()
    return SweetbookClient(s.sweetbook_api_key, s.sweetbook_env)


class OrderBody(BaseModel):
    spec: dict
    shipping: dict


@router.post("/projects/{project_id}/order")
def create_order(project_id: str, body: OrderBody, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    if project.status != "ready":
        raise HTTPException(409, "집필과 퇴고를 마친 뒤 주문할 수 있습니다")
    client = get_sweetbook_client()
    try:
        book_uid = TemplateRenderer(client).render(project, project.pages, body.spec)
        order = client.create_order({"bookUid": book_uid, **body.shipping})
    except SweetbookError as e:
        # 왜 메시지를 매핑하는가: Sweetbook 원문 에러를 그대로 노출하지 않는다(설계서 §9)
        raise HTTPException(502, f"주문에 실패했습니다: {e}")
    project.sweetbook_book_id = book_uid
    project.sweetbook_order_id = order.get("orderUid")
    project.order_status = "ORDERED"
    project.status = "ordered"
    db.commit()
    return {"book_uid": book_uid, "order_uid": project.sweetbook_order_id}


@router.get("/projects/{project_id}/order/status")
def order_status(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    return {"order_status": project.order_status}


class WebhookBody(BaseModel):
    orderUid: str
    status: str


@router.post("/webhooks/sweetbook")
def webhook(body: WebhookBody, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(sweetbook_order_id=body.orderUid).first()
    if project:
        project.order_status = body.status
        db.commit()
    return {"ok": True}
