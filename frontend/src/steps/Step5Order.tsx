/** 위자드 5단계: 배송 정보 입력 → Sweetbook 주문 → 주문번호/상태 표시. */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createOrder, getOrderStatus } from "../api";
import Wizard from "../Wizard";

// 파트너 포털에서 확인한 Sandbox 판형/템플릿 UID로 교체할 것 (Task 9 Step 5에서 확정)
const BOOK_SPEC = { bookSpecUid: "REPLACE_ME", coverTemplateUid: "REPLACE_ME", contentTemplateUid: "REPLACE_ME" };

const STATUS_KO: Record<string, string> = {
  ORDERED: "주문 접수", PRINTING: "인쇄 중", BINDING: "제본 중",
  SHIPPING: "배송 중", DELIVERED: "배송 완료", CANCELLED: "주문 취소",
};

export default function Step5Order() {
  const { id = "" } = useParams();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [orderUid, setOrderUid] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!orderUid) return;
    const t = setInterval(async () => {
      const { order_status } = await getOrderStatus(id);
      setStatus(order_status);
    }, 5000);
    return () => clearInterval(t);
  }, [id, orderUid]);

  const submit = async () => {
    if (!name || !address) return setError("받는 분과 주소를 적어주세요");
    setError("");
    setBusy(true);
    try {
      const res = await createOrder(id, BOOK_SPEC, { name, phone, address });
      setOrderUid(res.order_uid);
      setStatus("ORDERED");
    } catch (e) {
      setError(e instanceof Error ? e.message : "주문에 실패했어요. 잠시 후 다시 시도해주세요");
    } finally { setBusy(false); }
  };

  if (orderUid) return (
    <Wizard step="order">
      <h2>책이 인쇄소로 떠났어요</h2>
      <div className="book-page" style={{ textAlign: "center" }}>
        <p className="marker">주문번호</p>
        <p style={{ fontSize: 18, fontWeight: 600, letterSpacing: "0.06em" }}>{orderUid}</p>
        <p style={{ marginTop: 14 }}>{STATUS_KO[status ?? ""] ?? status}</p>
        <p className="muted" style={{ marginTop: 14, fontSize: 13 }}>
          인쇄와 제본이 끝나면 배송이 시작됩니다.<br />이 화면은 상태가 바뀔 때마다 갱신돼요.
        </p>
      </div>
    </Wizard>
  );

  return (
    <Wizard step="order">
      <h2>어디로 보내드릴까요</h2>
      <p className="muted">완성된 원고가 실물 책으로 인쇄되어 도착합니다.</p>

      <label htmlFor="o-name">받는 분</label>
      <input id="o-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="이름" />
      <label htmlFor="o-phone">연락처</label>
      <input id="o-phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="010-0000-0000" />
      <label htmlFor="o-addr">주소</label>
      <input id="o-addr" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="책이 도착할 곳" />

      {error && <p className="error-text" role="alert">{error}</p>}
      <div className="bottom-bar">
        <button className="btn-primary" onClick={submit} disabled={busy}>
          {busy ? "책을 만드는 중…" : "실물 책 주문하기"}
        </button>
      </div>
    </Wizard>
  );
}
