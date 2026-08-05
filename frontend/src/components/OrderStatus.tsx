/** 주문 현황: 내 책 + 수령인별 인쇄/배송 상태를 폴링해 보여준다(웹훅으로 갱신됨).
 *  누가 호출: screens/Album(status 뷰).
 *  무엇을 호출: api(getOrderStatus). */
import { useEffect, useState } from "react";
import { getOrderStatus } from "../api";

// Sweetbook orderStatus enum 전체(docs/operations/order-status) — 서버가 주는 값 그대로 들어온다.
const LABEL: Record<string, string> = {
  PAID: "주문 완료", PDF_READY: "인쇄 준비 중", CONFIRMED: "제작 확정",
  IN_PRODUCTION: "인쇄 중", COMPLETED: "제작 완료", PRODUCTION_COMPLETE: "제작 완료",
  SHIPPED: "배송 중", DELIVERED: "배송 완료",
  CANCELLED: "취소됨", CANCELLED_REFUND: "취소됨 (환불)", ERROR: "오류",
};
const label = (s: string | null) => (s ? LABEL[s] ?? s : "대기 중");

export default function OrderStatus({ projectId }: { projectId: string }) {
  const [data, setData] = useState<{ order_status: string | null; recipients: { name: string; order_status: string | null }[] } | null>(null);

  useEffect(() => {
    let live = true;
    const tick = () => getOrderStatus(projectId).then((d) => { if (live) setData(d); }).catch(() => {});
    tick();
    const t = setInterval(tick, 5000);
    return () => { live = false; clearInterval(t); };
  }, [projectId]);

  if (!data) return <div style={{ padding: 80, textAlign: "center", color: "var(--soft)" }}>여는 중…</div>;
  return (
    <div style={{ padding: "76px var(--gut) 40px" }}>
      <p className="kicker">SWEETBOOK · 인쇄·배송</p>
      <h2 className="order-h">주문 현황</h2>
      <div className="receipt" style={{ marginTop: 18 }}>
        <div className="receipt-row"><span>내 책</span><b>{label(data.order_status)}</b></div>
        {data.recipients.map((r) => (
          <div key={r.name} className="receipt-row"><span>{r.name} (선물)</span><b>{label(r.order_status)}</b></div>
        ))}
      </div>
      <p className="ship-note" style={{ marginTop: 12 }}>상태는 자동으로 갱신돼요</p>
    </div>
  );
}
