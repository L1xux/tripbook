"""수령인·주문·웹훅 라우터. / main.py가 등록. / sweetbook 모듈 호출."""
import hashlib
import hmac
import json
import time
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, Request
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


def _order_payload(book_uid: str, shipping: dict, external_ref: str) -> dict:
    # externalRef: 파트너 포털에서 이 주문이 우리 어느 여행/수령인인지 역추적하기 위한 식별자(최대 100자)
    return {"items": [{"bookUid": book_uid, "quantity": 1}],
            "shipping": _shipping(shipping), "externalRef": external_ref[:100]}


def _idem_key(prefix: str, payload: dict) -> str:
    """멱등 키는 본문에서 결정적으로 만든다. Sweetbook은 4xx 응답도 키에 24시간 캐시하고
    같은 키+다른 본문을 422로 거부하므로 — 고정 키를 쓰면 '주소 오타로 실패 → 고쳐서 재시도'가
    24시간 잠긴다. 같은 본문 재시도는 같은 키(이중 차감 방지), 고친 본문은 자연히 새 키."""
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _place_order(client, payload: dict, key: str) -> dict:
    """주문 1건. 충전금 부족은 재시도해도 소용없으므로 즉시 402로 끊는다(다른 수령인도 같은 지갑)."""
    try:
        return client.create_order(payload, idempotency_key=key)
    except SweetbookError as e:
        if e.code == "ERR_INSUFFICIENT_CREDIT":
            raise HTTPException(402, "충전금이 부족해 주문하지 못했어요. 충전 후 다시 시도해주세요") from e
        raise


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
            payload = _order_payload(book_uid, body.shipping, f"tripbook:{project.id}:me")
            me = _place_order(client, payload, key=_idem_key(f"tripbook-{project.id}-me", payload))
            project.sweetbook_order_id = me.get("orderUid")
            project.order_status = me.get("orderStatus", "PAID")  # 상태 문자열은 Sweetbook 것을 그대로 쓴다
            db.commit()  # 성공을 즉시 보존 — 이후 수령인이 실패해도 내 주문은 남는다
        except SweetbookError:
            failed.append(my_name)
    if project.sweetbook_order_id:
        orders.append({"to": my_name, "order_uid": project.sweetbook_order_id})

    # 수령인마다 1권 — 아직 주문되지 않은 사람만
    for r in project.recipients:
        if not r.sweetbook_order_id:
            try:
                payload = _order_payload(
                    book_uid,
                    {"name": r.name, "address": r.address, "phone": r.phone, "postalCode": r.postal_code},
                    f"tripbook:{project.id}:{r.id}")
                o = _place_order(client, payload, key=_idem_key(f"tripbook-{project.id}-{r.id}", payload))
                r.sweetbook_order_id = o.get("orderUid"); r.order_status = o.get("orderStatus", "PAID")
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


# 주문 상태 흐름(docs/operations/order-status). 값이 클수록 뒤 단계 — 늦게 도착한 과거 이벤트를 걸러내는 데 쓴다.
STATUS_RANK = {"PAID": 1, "PDF_READY": 2, "CONFIRMED": 3, "IN_PRODUCTION": 4,
               "COMPLETED": 5, "PRODUCTION_COMPLETE": 5, "SHIPPED": 6, "DELIVERED": 7,
               "CANCELLED": 9, "CANCELLED_REFUND": 9, "ERROR": 9}
TERMINAL_STATUSES = {"CANCELLED", "CANCELLED_REFUND", "ERROR"}
WEBHOOK_MAX_SKEW_SEC = 300  # 서명 재사용(replay) 방지


def _verify_webhook(request: Request, raw: bytes) -> None:
    """X-Webhook-Signature = "sha256=" + HMAC-SHA256(secretKey, "{timestamp}.{raw body}") 검증.
    시크릿 미설정(로컬 개발)이면 생략한다 — 공개 배포 전 반드시 설정할 것."""
    secret = get_settings().sweetbook_webhook_secret
    if not secret:
        return
    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    if not signature or not timestamp:
        raise HTTPException(401, "서명 헤더가 없습니다")
    try:
        skew = abs(time.time() - int(timestamp))
    except ValueError:
        raise HTTPException(401, "타임스탬프 형식이 올바르지 않습니다")
    if skew > WEBHOOK_MAX_SKEW_SEC:
        raise HTTPException(401, "만료된 서명입니다")
    expected = "sha256=" + hmac.new(secret.encode(), timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "서명이 일치하지 않습니다")


def _should_apply(current: str | None, new: str) -> bool:
    """재시도(최대 3회)로 순서가 뒤바뀐 재전송이 최신 상태를 되돌리지 않게 한다.
    취소·오류는 흐름 밖 상태라 항상 반영한다. 모르는 상태값은 막지 않는다(앞으로 늘 수 있으므로)."""
    if new in TERMINAL_STATUSES or current is None:
        return True
    new_rank, current_rank = STATUS_RANK.get(new), STATUS_RANK.get(current)
    if new_rank is None or current_rank is None:
        return True
    return new_rank >= current_rank


@router.post("/webhooks/sweetbook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Sweetbook 주문 상태 웹훅. 본문은 {event_uid, event_type, created_at, data{order_uid, order_status}}.
    서명 검증에 원문 바이트가 필요해 Pydantic 파싱 대신 raw body를 직접 읽는다."""
    raw = await request.body()
    _verify_webhook(request, raw)
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "본문을 해석할 수 없습니다")

    data = payload.get("data") or {}
    order_uid, status = data.get("order_uid"), data.get("order_status")
    # 주문 상태와 무관한 이벤트(항목 부분취소 등)나 모르는 주문도 200으로 받는다 — 4xx면 3회 재시도를 유발한다.
    if not order_uid or not status:
        return {"ok": True, "applied": False}

    applied = False
    project = db.query(Project).filter_by(sweetbook_order_id=order_uid).first()
    if project and _should_apply(project.order_status, status):
        project.order_status = status
        applied = True
    r = db.query(Recipient).filter_by(sweetbook_order_id=order_uid).first()
    if r and _should_apply(r.order_status, status):
        r.order_status = status
        applied = True
    db.commit()
    return {"ok": True, "applied": applied}
