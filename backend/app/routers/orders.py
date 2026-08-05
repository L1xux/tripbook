"""판형·수령인·주문·웹훅 라우터. / main.py가 등록. / sweetbook 모듈 호출."""
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


class RecipientPatch(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    postal_code: str | None = None
    gift_message: str | None = None


@router.post("/projects/{project_id}/recipients", status_code=201)
def add_recipient(project_id: str, body: RecipientBody, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    r = Recipient(project_id=project_id, **body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id}


def _mutable_recipient_or_409(db, recipient_id: str) -> Recipient:
    """주문이 나간 수령인은 바꿀 수 없다. 책은 옛 주소로 인쇄되는데 우리 쪽만 바뀌거나 배송 추적이 사라진다."""
    r = get_or_404(db, Recipient, recipient_id, "recipient")
    if r.sweetbook_order_id:
        raise HTTPException(409, "이미 인쇄가 시작된 선물이라 변경할 수 없어요")
    return r


@router.patch("/recipients/{recipient_id}")
def patch_recipient(recipient_id: str, body: RecipientPatch, db: Session = Depends(get_db)):
    r = _mutable_recipient_or_409(db, recipient_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/recipients/{recipient_id}")
def remove_recipient(recipient_id: str, db: Session = Depends(get_db)):
    r = _mutable_recipient_or_409(db, recipient_id)
    db.delete(r); db.commit()
    return {"ok": True}


@router.get("/book-spec")
def book_spec(pages: int | None = None):
    """판형 이름·단가·템플릿 uid의 단일 출처. 단가는 계약가라 캐시하지 않고 매번 받아온다."""
    s = get_settings()
    try:
        spec = get_sweetbook_client().get_book_spec(s.sweetbook_book_spec_uid)
    except SweetbookError:
        raise HTTPException(502, "판형 정보를 불러오지 못했습니다")

    page_min = int(spec.get("pageMin") or 0)
    increment = int(spec.get("pageIncrement") or 1) or 1
    # 순간이 적어도 여백 페이지로 채워 인쇄되므로 언제나 pageMin 이상으로 계산한다
    page_count = max(pages or page_min, page_min)
    steps = max(0, (page_count - page_min)) // increment
    price = int(spec.get("priceBase") or 0) + steps * int(spec.get("pricePerIncrement") or 0)
    return {
        "name": spec.get("name", ""),
        "price": price,
        "page_min": page_min,
        "page_max": spec.get("pageMax"),
        "page_increment": increment,
        "spec": {"bookSpecUid": s.sweetbook_book_spec_uid,
                 "coverTemplateUid": s.sweetbook_cover_template_uid,
                 "contentTemplateUid": s.sweetbook_content_template_uid},
    }


class OrderBody(BaseModel):
    # 판형·템플릿 uid는 서버 설정이 단일 출처다. 프론트가 안 보내면 그 값을 쓴다.
    spec: dict | None = None
    shipping: dict


class CancelBody(BaseModel):
    reason: str = "사용자 요청"


def _shipping(d: dict) -> dict:
    """우리 배송 정보를 Sweetbook shipping 스키마로 옮긴다.
    recipientName·recipientPhone·address1·postalCode가 필수다."""
    return {
        "recipientName": d.get("name") or d.get("recipientName") or "",
        "recipientPhone": d.get("phone") or d.get("recipientPhone") or "",
        "address1": d.get("address") or d.get("address1") or "",
        "address2": d.get("address2") or "",
        "postalCode": d.get("postalCode") or d.get("postal_code") or "",
    }


def _order_payload(book_uid: str, shipping: dict, external_ref: str) -> dict:
    # externalRef는 파트너 포털에서 어느 여행·수령인의 주문인지 역추적하는 식별자다. 최대 100자.
    return {"items": [{"bookUid": book_uid, "quantity": 1}],
            "shipping": _shipping(shipping), "externalRef": external_ref[:100]}


def _idem_key(prefix: str, payload: dict) -> str:
    """멱등 키를 본문에서 만든다. Sweetbook은 실패 응답도 24시간 캐시하고 같은 키에 다른 본문이 오면
    거부하므로, 고정 키를 쓰면 주소를 고쳐 재시도하는 길이 하루 동안 막힌다."""
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _require_enough_credit(client, book_uid: str, shipping: dict, copies: int) -> None:
    """결제 전에 차감 예정액과 잔액을 대조해, 부족하면 한 건도 결제하지 않는다.
    견적 호출 자체가 실패하면 막지 않는다. 주문이 어차피 402를 정확히 돌려준다."""
    if copies <= 0:
        return
    try:
        est = client.estimate_order({"items": [{"bookUid": book_uid, "quantity": copies}],
                                     "shipping": _shipping(shipping)})
    except SweetbookError:
        return
    if est.get("creditSufficient") is False:
        need, have = est.get("paidCreditAmount"), est.get("creditBalance")
        if isinstance(need, (int, float)) and isinstance(have, (int, float)):
            raise HTTPException(402, f"충전금이 부족해 주문하지 못했어요. 필요 {need:,.0f}원, 잔액 {have:,.0f}원")
        raise HTTPException(402, "충전금이 부족해 주문하지 못했어요")


def _place_order(client, payload: dict, key: str) -> dict:
    """주문 1건. 충전금 부족은 재시도해도 소용없으므로 즉시 402로 끊는다."""
    try:
        return client.create_order(payload, idempotency_key=key)
    except SweetbookError as e:
        if e.code == "ERR_INSUFFICIENT_CREDIT":
            raise HTTPException(402, "충전금이 부족해 주문하지 못했어요. 충전 후 다시 시도해주세요") from e
        raise


@router.post("/projects/{project_id}/order")
def create_order(project_id: str, body: OrderBody, db: Session = Depends(get_db)):
    """책 1권을 렌더하고 나와 수령인마다 1권씩 주문한다.
    성공할 때마다 즉시 커밋해, 일부 실패해도 성공분은 남고 재시도하면 실패분만 다시 주문한다."""
    project = get_project_or_404(db, project_id)
    if not project.photos:
        raise HTTPException(409, "순간을 하나 이상 담은 뒤 주문할 수 있습니다")
    client = get_sweetbook_client()

    # 이미 만든 책이 있으면 재사용해 재시도 때 중복 렌더를 막는다
    book_uid = project.sweetbook_book_id
    if not book_uid:
        s = get_settings()
        spec = body.spec or {"bookSpecUid": s.sweetbook_book_spec_uid,
                             "coverTemplateUid": s.sweetbook_cover_template_uid,
                             "contentTemplateUid": s.sweetbook_content_template_uid}
        try:
            book_uid = TemplateRenderer(client).render(project, project.photos, spec)
        except SweetbookError:
            raise HTTPException(502, "책 생성에 실패했습니다. 잠시 후 다시 시도해주세요")
        project.sweetbook_book_id = book_uid
        db.commit()

    orders: list[dict] = []
    failed: list[str] = []
    my_name = body.shipping.get("name", "나")

    # 한 권씩 결제하다 중간에 402가 나면 일부만 인쇄된다.
    # 견적은 최종화된 bookUid가 있어야 하므로 렌더 뒤인 여기서만 부를 수 있다.
    _require_enough_credit(client, book_uid, body.shipping,
                           copies=(0 if project.sweetbook_order_id else 1)
                           + sum(1 for r in project.recipients if not r.sweetbook_order_id))

    if not project.sweetbook_order_id:
        try:
            payload = _order_payload(book_uid, body.shipping, f"tripbook:{project.id}:me")
            me = _place_order(client, payload, key=_idem_key(f"tripbook-{project.id}-me", payload))
            project.sweetbook_order_id = me.get("orderUid")
            project.order_status = me.get("orderStatus", "PAID")  # 상태 문자열은 Sweetbook 것을 그대로 쓴다
            db.commit()  # 수령인이 실패해도 내 주문은 남는다
        except SweetbookError:
            failed.append(my_name)
    if project.sweetbook_order_id:
        orders.append({"to": my_name, "order_uid": project.sweetbook_order_id})

    for r in project.recipients:
        if not r.sweetbook_order_id:
            try:
                payload = _order_payload(
                    book_uid,
                    {"name": r.name, "address": r.address, "phone": r.phone, "postalCode": r.postal_code},
                    f"tripbook:{project.id}:{r.id}")
                o = _place_order(client, payload, key=_idem_key(f"tripbook-{project.id}-{r.id}", payload))
                r.sweetbook_order_id = o.get("orderUid"); r.order_status = o.get("orderStatus", "PAID")
                db.commit()
            except SweetbookError:
                failed.append(r.name)
                continue
        orders.append({"to": r.name, "order_uid": r.sweetbook_order_id})

    if failed:
        raise HTTPException(502, f"일부 주문에 실패했어요: {', '.join(failed)}. "
                                 "성공한 주문은 저장됐고, 다시 시도하면 실패분만 재주문합니다.")

    project.status = "ordered"
    db.commit()
    return {"book_uid": book_uid, "orders": orders}


CANCELLABLE_STATUSES = {"PAID", "PDF_READY"}  # 이후 단계는 제작이 시작돼 관리자 승인이 필요하다


@router.post("/projects/{project_id}/order/cancel")
def cancel_order(project_id: str, body: CancelBody, db: Session = Depends(get_db)):
    """내 책과 선물을 모두 취소하고 충전금을 돌려받는다. 제작이 시작되기 전에만 가능하다."""
    project = get_project_or_404(db, project_id)
    targets = [(project, project.sweetbook_order_id)] + [(r, r.sweetbook_order_id) for r in project.recipients]
    targets = [(row, uid) for row, uid in targets if uid]
    if not targets:
        raise HTTPException(409, "아직 주문한 책이 없어요")

    blocked = [row for row, _ in targets if (row.order_status or "PAID") not in CANCELLABLE_STATUSES]
    if blocked:
        raise HTTPException(409, "이미 제작이 시작돼 취소할 수 없어요")

    client = get_sweetbook_client()
    failed: list[str] = []
    for row, uid in targets:
        try:
            res = client.cancel_order(uid, body.reason, idempotency_key=f"tripbook-cancel-{uid}")
            row.order_status = res.get("orderStatus", "CANCELLED_REFUND")
            row.sweetbook_order_id = None  # 번호를 비워 재주문이 새 주문으로 나가게 한다
            db.commit()  # 뒤가 실패해도 앞의 환불은 기록된다
        except SweetbookError:
            failed.append(getattr(row, "name", "내 책"))
    if failed:
        raise HTTPException(502, f"일부 취소에 실패했어요: {', '.join(failed)}. 다시 시도해주세요")

    project.status = "draft"  # 다시 담고 주문할 수 있는 상태로
    db.commit()
    return {"ok": True, "cancelled": len(targets)}


REMOTE_REFRESH_INTERVAL_SEC = 30
_last_remote_refresh: dict[str, float] = {}


def _may_ask_sweetbook(project_id: str) -> bool:
    """주문 현황 화면은 5초마다 폴링한다. 원격 조회까지 그 주기로 내보내면 Rate Limit을 금방 갉아먹으므로
    30초에 한 번으로 묶는다. 상태는 웹훅이 밀어주는 값이라 DB만 읽어도 화면은 같다.
    조회에 실패해도 시각을 갱신해, Sweetbook이 아플 때 재시도가 몰리지 않게 한다."""
    now = time.monotonic()
    last = _last_remote_refresh.get(project_id)
    if last is not None and now - last < REMOTE_REFRESH_INTERVAL_SEC:
        return False
    if len(_last_remote_refresh) > 1000:  # 지난 항목만 청소해 무한히 쌓이지 않게 한다
        stale = now - REMOTE_REFRESH_INTERVAL_SEC
        for key in [k for k, v in _last_remote_refresh.items() if v < stale]:
            _last_remote_refresh.pop(key, None)
    _last_remote_refresh[project_id] = now
    return True


def _refresh_from_sweetbook(db, project: Project) -> None:
    """웹훅이 등록되기 전에는 상태가 PAID에서 멈추므로 진행 중인 주문만 원격에서 당겨온다.
    Sweetbook이 죽어도 화면은 마지막으로 아는 상태로 떠야 하므로 실패는 넘긴다."""
    rows = [(project, project.sweetbook_order_id)] + [(r, r.sweetbook_order_id) for r in project.recipients]
    pending = [(row, uid) for row, uid in rows
               if uid and (row.order_status or "") not in TERMINAL_STATUSES and row.order_status != "DELIVERED"]
    if not pending or not _may_ask_sweetbook(project.id):
        return
    try:
        client = get_sweetbook_client()
    except Exception:
        return
    changed = False
    for row, uid in pending:
        try:
            remote = client.get_order(uid).get("orderStatus")
        except SweetbookError:
            continue
        # 조회가 과거 상태를 주더라도 뒤로 돌리지 않는다
        if remote and _should_apply(row.order_status, remote):
            row.order_status = remote
            changed = True
    if changed:
        db.commit()


@router.get("/projects/{project_id}/order/status")
def order_status(project_id: str, db: Session = Depends(get_db)):
    project = get_project_or_404(db, project_id)
    _refresh_from_sweetbook(db, project)
    return {"order_status": project.order_status,
            "cancellable": bool(project.sweetbook_order_id)
            and (project.order_status or "PAID") in CANCELLABLE_STATUSES,
            "recipients": [{"name": r.name, "order_status": r.order_status} for r in project.recipients]}


# 주문 상태 흐름. 값이 클수록 뒤 단계이며, 늦게 도착한 과거 이벤트를 걸러내는 데 쓴다.
STATUS_RANK = {"PAID": 1, "PDF_READY": 2, "CONFIRMED": 3, "IN_PRODUCTION": 4,
               "COMPLETED": 5, "PRODUCTION_COMPLETE": 5, "SHIPPED": 6, "DELIVERED": 7,
               "CANCELLED": 9, "CANCELLED_REFUND": 9, "ERROR": 9}
TERMINAL_STATUSES = {"CANCELLED", "CANCELLED_REFUND", "ERROR"}
WEBHOOK_MAX_SKEW_SEC = 300  # 서명 재사용 방지


def _verify_webhook(request: Request, raw: bytes) -> None:
    """X-Webhook-Signature를 HMAC-SHA256으로 검증한다. 서명 대상은 "{timestamp}.{원문}".
    시크릿이 없으면 검증을 생략하므로 공개 배포 전 반드시 설정해야 한다."""
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
    """순서가 뒤바뀐 재전송이 최신 상태를 되돌리지 않게 한다.
    취소와 오류는 흐름 밖이라 항상 반영하고, 모르는 상태값은 막지 않는다."""
    if new in TERMINAL_STATUSES or current is None:
        return True
    new_rank, current_rank = STATUS_RANK.get(new), STATUS_RANK.get(current)
    if new_rank is None or current_rank is None:
        return True
    return new_rank >= current_rank


@router.post("/webhooks/sweetbook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Sweetbook 주문 상태 웹훅. 본문은 event_uid·event_type·created_at·data로 온다.
    서명 검증에 원문 바이트가 필요해 Pydantic 대신 raw body를 직접 읽는다."""
    raw = await request.body()
    _verify_webhook(request, raw)
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "본문을 해석할 수 없습니다")

    data = payload.get("data") or {}
    order_uid, status = data.get("order_uid"), data.get("order_status")
    # 상태와 무관한 이벤트나 모르는 주문도 200으로 받는다. 4xx면 재시도를 부른다.
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
