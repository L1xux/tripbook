/** 주문 + 선물: 내 배송 입력 + (동행자에게) 선물 한 권 추가 → Sweetbook 주문. 완료 시 주문번호/상태.
 *  누가 호출: screens/Album(order 뷰).
 *  무엇을 호출: api(addRecipient/createOrder). */
import { useState } from "react";
import { addRecipient, createOrder, type Project } from "../api";

const BOOK_PRICE = 12600; // SQUAREBOOK_HC 기본가 — 배송비는 결제 시 계산
// Sweetbook Sandbox 확정값: 스퀘어 하드커버(SQUAREBOOK_HC) + 표지 "일기장A"(taupe/명조, 우리 디자인과 일치) + 공용 빈내지
const BOOK_SPEC = { bookSpecUid: "SQUAREBOOK_HC", coverTemplateUid: "79yjMH3qRPly", contentTemplateUid: "2mi1ao0Z4Vxl" };

export default function OrderSheet({ project, onViewStatus }: { project: Project; onViewStatus?: () => void }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [postal, setPostal] = useState("");
  const [address, setAddress] = useState("");
  const [gift, setGift] = useState(false);
  const [giftName, setGiftName] = useState(project.companions ?? "");
  const [giftPhone, setGiftPhone] = useState("");
  const [giftPostal, setGiftPostal] = useState("");
  const [giftAddr, setGiftAddr] = useState("");
  const [done, setDone] = useState<{ orders: { to: string; order_uid: string }[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const copies = gift ? 2 : 1;
  const subtotal = BOOK_PRICE * copies;

  const submit = async () => {
    if (!name || !phone || !postal || !address) return setError("이름·연락처·우편번호·주소를 모두 적어주세요");
    if (gift && (!giftName || !giftPhone || !giftPostal || !giftAddr)) return setError("선물 받는 분의 정보도 모두 적어주세요");
    setError(""); setBusy(true);
    try {
      if (gift) await addRecipient(project.id, { name: giftName, address: giftAddr, phone: giftPhone, postal_code: giftPostal });
      const res = await createOrder(project.id, BOOK_SPEC, { name, phone, postalCode: postal, address });
      setDone(res);
    } catch (e) { setError(e instanceof Error ? e.message : "주문에 실패했어요"); } finally { setBusy(false); }
  };

  if (done) return (
    <div style={{ padding: "76px 22px" }}>
      <p className="kicker">SWEETBOOK · 인쇄 접수</p>
      <h2 className="order-h">책이 인쇄소로 떠났어요</h2>
      <div className="receipt">
        {done.orders.map((o) => (
          <div key={o.order_uid} className="receipt-row">
            <span>{o.to}</span><b>{o.order_uid}</b>
          </div>
        ))}
        <p className="muted receipt-note">인쇄와 제본이 끝나면 배송이 시작돼요. 진행 상황은 문자로 알려드려요.</p>
      </div>
      {onViewStatus && (
        <button className="btn" style={{ width: "100%", marginTop: 18 }} onClick={onViewStatus}>주문 현황 보기</button>
      )}
    </div>
  );

  return (
    <div style={{ padding: "76px 22px 120px" }}>
      <p className="kicker">{(project.title || "TRIP").toUpperCase()} · {project.photos.length}개의 순간</p>
      <h2 className="order-h">한 권으로 만들어요</h2>
      <p className="muted order-sub">이 순간들이 손에 쥐는 한 권의 책이 됩니다.</p>

      <label>받는 분</label>
      <input placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} />
      <div className="field-row">
        <input placeholder="연락처" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <input placeholder="우편번호" inputMode="numeric" value={postal} onChange={(e) => setPostal(e.target.value)} style={{ maxWidth: 130 }} />
      </div>
      <input placeholder="주소" value={address} onChange={(e) => setAddress(e.target.value)} style={{ marginTop: 8 }} />

      <div className="gift">
        <div className="g-top">
          <div className="g-face" />
          <div><b>{project.companions || "함께한 사람"}에게도 한 권</b><span>같은 책을 선물로 보내기</span></div>
          <div className={"toggle" + (gift ? " on" : "")} onClick={() => setGift((g) => !g)} role="switch" aria-checked={gift}><b /></div>
        </div>
        {gift && (
          <div className="gift-fields">
            <input placeholder="받는 분 이름" value={giftName} onChange={(e) => setGiftName(e.target.value)} />
            <div className="field-row">
              <input placeholder="연락처" inputMode="tel" value={giftPhone} onChange={(e) => setGiftPhone(e.target.value)} />
              <input placeholder="우편번호" inputMode="numeric" value={giftPostal} onChange={(e) => setGiftPostal(e.target.value)} style={{ maxWidth: 130 }} />
            </div>
            <input placeholder="선물 배송 주소" value={giftAddr} onChange={(e) => setGiftAddr(e.target.value)} />
          </div>
        )}
      </div>

      <div className="total">
        <span>책 {copies}권</span><b>{subtotal.toLocaleString()}원</b>
      </div>
      <p className="ship-note">배송비는 결제 단계에서 계산돼요</p>

      {error && <p className="error-text">{error}</p>}
      <div className="bottom-bar">
        <button className="btn" style={{ width: "100%" }} disabled={busy} onClick={submit}>
          {busy ? "책을 만드는 중…" : `주문하기 · ${subtotal.toLocaleString()}원`}
        </button>
      </div>
    </div>
  );
}
