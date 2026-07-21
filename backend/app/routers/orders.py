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
    except SweetbookError:
        raise HTTPException(502, "주문에 실패했습니다. 잠시 후 다시 시도해주세요")
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
