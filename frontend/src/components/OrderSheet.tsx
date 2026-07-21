/** 주문 + 선물: 내 배송 입력 + (동행자에게) 선물 한 권 추가 → Sweetbook 주문. 완료 시 주문번호/상태.
 *  누가 호출: screens/Album(order 뷰).
 *  무엇을 호출: api(addRecipient/createOrder). */
import { useState } from "react";
import { addRecipient, createOrder, type Project } from "../api";

const PRICE = 24000;
// Sweetbook Sandbox 확정값: 스퀘어 하드커버(SQUAREBOOK_HC) + 표지 "일기장A"(taupe/명조, 우리 디자인과 일치) + 공용 빈내지
const BOOK_SPEC = { bookSpecUid: "SQUAREBOOK_HC", coverTemplateUid: "79yjMH3qRPly", contentTemplateUid: "2mi1ao0Z4Vxl" };

export default function OrderSheet({ project }: { project: Project }) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [gift, setGift] = useState(false);
  const [giftName, setGiftName] = useState(project.companions ?? "");
  const [giftAddr, setGiftAddr] = useState("");
  const [done, setDone] = useState<{ orders: { to: string; order_uid: string }[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const total = PRICE * (gift ? 2 : 1);

  const submit = async () => {
    if (!name || !address) return setError("받는 분과 주소를 적어주세요");
    setError(""); setBusy(true);
    try {
      if (gift && giftName && giftAddr) await addRecipient(project.id, { name: giftName, address: giftAddr });
      const res = await createOrder(project.id, BOOK_SPEC, { name, address });
      setDone(res);
    } catch (e) { setError(e instanceof Error ? e.message : "주문에 실패했어요"); } finally { setBusy(false); }
  };

  if (done) return (
    <div style={{ padding: "70px 22px" }}>
      <h2 style={{ font: "800 22px/1.3 var(--sans)" }}>책이 인쇄소로 떠났어요</h2>
      <div className="book-page" style={{ marginTop: 16 }}>
        {done.orders.map((o) => <p key={o.order_uid} style={{ margin: "6px 0" }}>{o.to} · <b>{o.order_uid}</b></p>)}
        <p className="muted" style={{ marginTop: 12, fontSize: 13 }}>인쇄와 제본이 끝나면 배송이 시작됩니다.</p>
      </div>
    </div>
  );

  return (
    <div style={{ padding: "70px 22px 24px" }}>
      <h2 style={{ font: "800 22px/1.3 var(--sans)" }}>한 권으로 만들어요</h2>
      <p className="muted" style={{ margin: "6px 0 20px", fontSize: 13 }}>{project.photos.length}개의 순간이 손에 쥐는 한 권이 됩니다.</p>
      <label>받는 분</label><input value={name} onChange={(e) => setName(e.target.value)} />
      <label>주소</label><input value={address} onChange={(e) => setAddress(e.target.value)} />

      <div className="gift">
        <div className="g-top"><div className="g-face" /><div><b>{project.companions || "함께한 사람"}에게도 한 권</b><span>같은 책을 선물로 보내기</span></div></div>
        <div className="g-row"><span className="lab">선물 추가 · {PRICE.toLocaleString()}원</span>
          <div className={"toggle" + (gift ? " on" : "")} onClick={() => setGift((g) => !g)}><b /></div></div>
        {gift && (<div style={{ marginTop: 10 }}>
          <input placeholder="받는 분 이름" value={giftName} onChange={(e) => setGiftName(e.target.value)} />
          <input placeholder="선물 배송 주소" value={giftAddr} onChange={(e) => setGiftAddr(e.target.value)} style={{ marginTop: 8 }} />
        </div>)}
      </div>

      <div className="total"><span>합계</span><b>{total.toLocaleString()}원</b></div>
      {error && <p className="error-text">{error}</p>}
      <button className="btn" style={{ width: "100%" }} disabled={busy} onClick={submit}>{busy ? "책을 만드는 중…" : "주문하기"}</button>
      <p style={{ font: "400 11px/1.6 var(--mono)", color: "var(--soft)", textAlign: "center", marginTop: 12 }}>SWEETBOOK 인쇄·배송</p>
    </div>
  );
}
