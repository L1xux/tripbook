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
    postal_code: str | None = None
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


def _shipping(d: dict) -> dict:
    """우리 배송 dict(name/address/phone…)를 Sweetbook 주문 shipping 스키마로 매핑.
    Sandbox 실검증: recipientName/recipientPhone/address1/postalCode가 필수."""
    return {
        "recipientName": d.get("name") or d.get("recipientName") or "",
        "recipientPhone": d.get("phone") or d.get("recipientPhone") or "",
        "address1": d.get("address") or d.get("address1") or "",
        "address2": d.get("address2") or "",
        "postalCode": d.get("postalCode") or d.get("postal_code") or "",
    }


def _order_payload(book_uid: str, shipping: dict) -> dict:
    return {"items": [{"bookUid": book_uid, "quantity": 1}], "shipping": _shipping(shipping)}


@router.post("/projects/{project_id}/order")
def create_order(project_id: str, body: OrderBody, db: Session = Depends(get_db)):
    """책 1권 렌더 → 나 + 수령인마다 1권 주문. 각 외부 성공을 즉시 커밋하고, 이미 주문된 건 건너뛴다.
    일부 실패해도 성공분은 보존되고, 재시도하면 실패분만 재주문한다(중복 주문 방지)."""
    project = get_project_or_404(db, project_id)
    if not project.photos:
        raise HTTPException(409, "순간을 하나 이상 담은 뒤 주문할 수 있습니다")
    client = get_sweetbook_client()

    # 책은 1회만 렌더 — 이미 만든 책이 있으면 재사용해 재시도 시 중복 렌더/주문을 막는다
    book_uid = project.sweetbook_book_id
    if not book_uid:
        try:
            book_uid = TemplateRenderer(client).render(project, project.photos, body.spec)
        except SweetbookError:
            raise HTTPException(502, "책 생성에 실패했습니다. 잠시 후 다시 시도해주세요")
        project.sweetbook_book_id = book_uid
        db.commit()  # 렌더 성공을 즉시 보존(재시도 시 재렌더 방지)

    orders: list[dict] = []
    failed: list[str] = []

    # 나에게 1권 — 아직 주문되지 않았을 때만(재시도 안전)
    my_name = body.shipping.get("name", "나")
    if not project.sweetbook_order_id:
        try:
            me = client.create_order(_order_payload(book_uid, body.shipping))
            project.sweetbook_order_id = me.get("orderUid")
            project.order_status = "ORDERED"
            db.commit()  # 성공을 즉시 보존 — 이후 수령인이 실패해도 내 주문은 남는다
        except SweetbookError:
            failed.append(my_name)
    if project.sweetbook_order_id:
        orders.append({"to": my_name, "order_uid": project.sweetbook_order_id})

    # 수령인마다 1권 — 아직 주문되지 않은 사람만
    for r in project.recipients:
        if not r.sweetbook_order_id:
            try:
                o = client.create_order(_order_payload(book_uid, {"name": r.name, "address": r.address, "phone": r.phone, "postalCode": r.postal_code}))
                r.sweetbook_order_id = o.get("orderUid"); r.order_status = "ORDERED"
                db.commit()  # 각 성공을 즉시 보존
            except SweetbookError:
                failed.append(r.name)
                continue
        orders.append({"to": r.name, "order_uid": r.sweetbook_order_id})

    if failed:
        # 일부만 성공 — 성공분은 이미 커밋됨. 다시 시도하면 위 건너뛰기로 실패분만 재주문한다.
        raise HTTPException(502, f"일부 주문에 실패했어요({', '.join(failed)}). 성공한 주문은 저장됐고, 다시 시도하면 실패분만 재주문합니다.")

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
