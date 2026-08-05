"""Sweetbook 운영·점검 CLI(앱 흐름 밖에서 쓰는 것들을 여기로 모았다).
누가 호출: 사람이 터미널에서. / 무엇을 호출: app.sweetbook.client.

  python scripts/sweetbook_ops.py credits              충전금 잔액
  python scripts/sweetbook_ops.py transactions [N]     최근 거래 N건(기본 10)
  python scripts/sweetbook_ops.py charge 100000        Sandbox 테스트 충전
  python scripts/sweetbook_ops.py specs                판형 목록(계약 단가 포함)
  python scripts/sweetbook_ops.py templates [kind]     템플릿 목록(cover|content|…)
  python scripts/sweetbook_ops.py books [N]            최근 만든 책 N권
  python scripts/sweetbook_ops.py order <orderUid>     주문 상세
  python scripts/sweetbook_ops.py cancel <orderUid> [사유]
  python scripts/sweetbook_ops.py webhook show
  python scripts/sweetbook_ops.py webhook register https://…/api/v1/webhooks/sweetbook
  python scripts/sweetbook_ops.py webhook delete
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.sweetbook.client import SweetbookClient, SweetbookError  # noqa: E402


def _client() -> SweetbookClient:
    s = get_settings()
    if not s.sweetbook_api_key:
        raise SystemExit("SWEETBOOK_API_KEY가 없습니다 (backend/.env)")
    return SweetbookClient(s.sweetbook_api_key, s.sweetbook_env)


def _won(v) -> str:
    return f"{v:,.0f}원" if isinstance(v, (int, float)) else str(v)


def cmd_credits(c, _):
    d = c.get_credits()
    print(f"계정 {d['accountUid']}  환경 {d['env']}\n잔액 {_won(d['balance'])}  (갱신 {d['updatedAt']})")


def cmd_transactions(c, args):
    n = int(args[0]) if args else 10
    for t in c.list_credit_transactions()[:n]:
        print(f"{t['createdAt'][:19]}  {t['direction']}{_won(abs(t['amount'])):>12}  "
              f"잔액 {_won(t['balanceAfter']):>12}  {t.get('reasonDisplay') or ''} {t.get('memo') or ''}")


def cmd_charge(c, args):
    if not args:
        raise SystemExit("금액을 지정하세요: charge 100000")
    d = c.charge_sandbox_credits(int(args[0]), memo="tripbook ops")
    print(f"충전 완료 — 잔액 {_won(d['balance'])} ({d['env']})")


def cmd_specs(c, _):
    for s in c.list_book_specs():
        print(f"{s['bookSpecUid']:<24} {s.get('name','')}\n"
              f"  {s.get('pageMin')}~{s.get('pageMax')}p (+{s.get('pageIncrement')}단위)  "
              f"기본 {_won(s.get('priceBase'))} + 증가분 {_won(s.get('pricePerIncrement'))}  "
              f"박스당 {s.get('booksPerBox')}권")


def cmd_templates(c, args):
    s = get_settings()
    params = {"bookSpecUid": s.sweetbook_book_spec_uid}
    if args:
        params["templateKind"] = args[0]
    used = {s.sweetbook_cover_template_uid: "← 우리 표지", s.sweetbook_content_template_uid: "← 우리 내지"}
    for t in c.list_templates(**params):
        uid = t.get("templateUid") or t.get("uid", "")
        print(f"{uid:<16} {t.get('templateKind',''):<8} {t.get('templateName') or t.get('name','')} {used.get(uid,'')}")


def cmd_books(c, args):
    n = int(args[0]) if args else 10
    for b in c.list_books()[:n]:
        print(f"{b['bookUid']:<18} {b.get('status',''):<12} {b.get('pageCount')}p  "
              f"{b.get('title','')}  {b.get('createdAt','')[:19]}")


def cmd_order(c, args):
    if not args:
        raise SystemExit("주문 uid가 필요합니다")
    d = c.get_order(args[0])
    print(f"{d['orderUid']}  {d.get('orderStatus')} ({d.get('orderStatusDisplay')})\n"
          f"  수령인 {d.get('recipientName')}  {d.get('postalCode')} {d.get('address1')}\n"
          f"  상품 {_won(d.get('totalProductAmount'))} + 배송 {_won(d.get('totalShippingFee'))} "
          f"= 차감 {_won(d.get('paidCreditAmount'))}\n"
          f"  externalRef {d.get('externalRef')}  주문 {d.get('orderedAt')}")


def cmd_cancel(c, args):
    if not args:
        raise SystemExit("주문 uid가 필요합니다")
    reason = args[1] if len(args) > 1 else "운영 취소"
    d = c.cancel_order(args[0], reason, idempotency_key=f"ops-cancel-{args[0]}")
    print(f"취소됨 — {d.get('orderStatus')}  환불 {_won(d.get('refundAmount'))}")


def cmd_webhook(c, args):
    action = args[0] if args else "show"
    if action == "show":
        try:
            d = c.get_webhook_config()
        except SweetbookError as e:
            print(f"등록된 웹훅이 없습니다 ({e})")
            return
        print(f"URL {d.get('webhookUrl')}\n활성 {d.get('isActive')}  이벤트 {d.get('events') or '전체'}\n"
              f"secretKey {d.get('secretKey')} (앞 8자만 노출됨 — 최초 등록 때만 전체값)")
    elif action == "register":
        if len(args) < 2:
            raise SystemExit("수신 URL이 필요합니다 (HTTPS만)")
        d = c.put_webhook_config(args[1], description="Tripbook 주문 상태 수신")
        secret = d.get("secretKey", "")
        print(f"등록 완료 — {d.get('webhookUrl')}")
        print(f"secretKey: {secret}")
        print("\n※ 전체값은 지금 한 번만 보입니다. backend/.env에 아래 줄을 넣고 서버를 재기동하세요:")
        print(f"SWEETBOOK_WEBHOOK_SECRET={secret}")
    elif action == "delete":
        c.delete_webhook_config()
        print("웹훅 해제 완료 (재등록하면 새 secretKey가 발급됩니다)")
    else:
        raise SystemExit(f"알 수 없는 동작: {action}")


COMMANDS = {"credits": cmd_credits, "transactions": cmd_transactions, "charge": cmd_charge,
            "specs": cmd_specs, "templates": cmd_templates, "books": cmd_books,
            "order": cmd_order, "cancel": cmd_cancel, "webhook": cmd_webhook}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 1
    try:
        COMMANDS[argv[0]](_client(), argv[1:])
    except SweetbookError as e:
        print(f"Sweetbook 오류: {e}" + (f" [{e.code}]" if e.code else ""))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
