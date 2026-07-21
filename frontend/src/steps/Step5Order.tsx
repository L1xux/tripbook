/** 위자드 5단계: 배송 정보 입력 → Sweetbook 주문 → 주문번호/상태 표시. */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createOrder, getOrderStatus } from "../api";

// 파트너 포털에서 확인한 Sandbox 판형/템플릿 UID로 교체할 것 (Task 9 Step 5에서 확정)
const BOOK_SPEC = { bookSpecUid: "REPLACE_ME", coverTemplateUid: "REPLACE_ME", contentTemplateUid: "REPLACE_ME" };

export default function Step5Order() {
  const { id = "" } = useParams();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [orderUid, setOrderUid] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!orderUid) return;
    const t = setInterval(async () => {
      const { order_status } = await getOrderStatus(id);
      setStatus(order_status);
    }, 5000);
    return () => clearInterval(t);
  }, [id, orderUid]);

  const submit = async () => {
    if (!name || !address) return alert("이름과 주소를 입력해주세요");
    setBusy(true);
    try {
      const res = await createOrder(id, BOOK_SPEC, { name, phone, address });
      setOrderUid(res.order_uid);
      setStatus("ORDERED");
    } catch (e) {
      alert(`주문에 실패했습니다. 잠시 후 다시 시도해주세요.\n${e}`);
    } finally { setBusy(false); }
  };

  if (orderUid) return (
    <div>
      <h2>주문이 완료되었어요 🎉</h2>
      <div className="card">
        <p>주문번호: <strong>{orderUid}</strong></p>
        <p>상태: <strong>{status}</strong></p>
        <p style={{ fontSize: 13, color: "#6b6558", marginTop: 8 }}>
          인쇄와 제본이 끝나면 배송이 시작됩니다.</p>
      </div>
    </div>
  );

  return (
    <div>
      <h2>어디로 보내드릴까요?</h2>
      <label>받는 분</label><input value={name} onChange={(e) => setName(e.target.value)} />
      <label>연락처</label><input value={phone} onChange={(e) => setPhone(e.target.value)} />
      <label>주소</label><input value={address} onChange={(e) => setAddress(e.target.value)} />
      <div className="bottom-bar">
        <button className="btn-primary" onClick={submit} disabled={busy}>
          {busy ? "책을 만드는 중..." : "실물 책 주문하기"}
        </button>
      </div>
    </div>
  );
}
