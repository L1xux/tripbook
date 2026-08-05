/** 내 책과 수령인별 인쇄·배송 상태를 폴링해 보여주고, 제작 전이면 취소할 수 있다.
 *  누가 호출: screens/Album의 주문 현황 화면.
 *  무엇을 호출: api의 getOrderStatus와 cancelOrder. */
import { useEffect, useState } from "react";
import { getOrderStatus, cancelOrder } from "../api";

// Sweetbook 주문 상태값. 서버가 주는 값이 그대로 들어온다.
const LABEL: Record<string, string> = {
  PAID: "주문 완료", PDF_READY: "인쇄 준비 중", CONFIRMED: "제작 확정",
  IN_PRODUCTION: "인쇄 중", COMPLETED: "제작 완료", PRODUCTION_COMPLETE: "제작 완료",
  SHIPPED: "배송 중", DELIVERED: "배송 완료",
  CANCELLED: "취소됨", CANCELLED_REFUND: "취소됨 (환불)", ERROR: "오류",
};
const label = (s: string | null) => (s ? LABEL[s] ?? s : "대기 중");

export default function OrderStatus({ projectId }: { projectId: string }) {
  const [data, setData] = useState<{ order_status: string | null; cancellable: boolean; recipients: { name: string; order_status: string | null }[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    const tick = () => getOrderStatus(projectId).then((d) => { if (live) setData(d); }).catch(() => {});
    tick();
    const t = setInterval(tick, 5000);
    return () => { live = false; clearInterval(t); };
  }, [projectId]);

  // 제작이 시작되기 전까지만 취소할 수 있고, 가능 여부는 서버가 판단해 내려준다
  const cancel = async () => {
    if (!confirm("주문을 취소할까요? 결제한 금액은 전액 환불돼요.")) return;
    setBusy(true); setError("");
    try {
      await cancelOrder(projectId, "사용자 요청");
      setData(await getOrderStatus(projectId));
    } catch (e) { setError(e instanceof Error ? e.message : "취소하지 못했어요"); }
    finally { setBusy(false); }
  };

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
      {error && <p className="error-text">{error}</p>}
      {data.cancellable && (
        <button className="btn-ghost" style={{ width: "100%", marginTop: 16 }} disabled={busy} onClick={cancel}>
          {busy ? "취소하는 중…" : "주문 취소하기"}
        </button>
      )}
    </div>
  );
}
