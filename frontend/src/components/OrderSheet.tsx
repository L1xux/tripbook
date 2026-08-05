/** 내 배송지를 받고, 원하면 동행자에게 보낼 한 권을 더해 주문한다.
 *  screens/Album의 주문 화면이 쓴다.
 *  api의 getBookSpec과 수령인 관련 함수, createOrder를 부른다. */
import { useEffect, useRef, useState } from "react";
import { addRecipient, removeRecipient, patchRecipient, createOrder, getBookSpec, type BookSpec, type Project } from "../api";

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
  // 이미 등록한 수령인 id. 재시도 때 중복 추가를 막고, 선물을 도로 끄면 등록을 취소하는 데 쓴다.
  // 등록만 남아 있으면 백엔드가 수령인 몫까지 주문해 화면에 보이는 권수와 실제가 어긋난다.
  const giftRid = useRef<string | null>(null);
  // 마지막으로 서버에 보낸 선물 정보. 값이 그대로면 수정을 보내지 않는다.
  // 선물 주문만 성공한 재시도에서 불필요한 수정이 409로 전체를 막는 것을 피한다.
  const giftSent = useRef<string | null>(null);
  const [spec, setSpec] = useState<BookSpec | null>(null);

  // 판형명과 단가는 Sweetbook 계약가다. 화면에 박아두면 단가가 바뀔 때 금액만 조용히 틀어진다.
  // 순간 수만큼 페이지가 늘어나므로 페이지 수를 함께 물어본다.
  useEffect(() => { getBookSpec(project.photos.length).then(setSpec).catch(() => setSpec(null)); },
            [project.photos.length]);

  const copies = gift ? 2 : 1;
  const subtotal = spec ? spec.price * copies : null;
  const won = (n: number) => `${n.toLocaleString()}원`;

  const submit = async () => {
    if (!name || !phone || !postal || !address) return setError("이름·연락처·우편번호·주소를 모두 적어주세요");
    if (gift && (!giftName || !giftPhone || !giftPostal || !giftAddr)) return setError("선물 받는 분의 정보도 모두 적어주세요");
    setError(""); setBusy(true);
    try {
      // 선물을 도로 껐으면 이전 시도에서 등록한 수령인을 취소한다. 그대로 두면 두 권이 주문된다.
      // 이미 인쇄가 시작됐으면 백엔드가 409로 거부하고, 그 메시지를 그대로 보여준다.
      if (!gift && giftRid.current) {
        await removeRecipient(giftRid.current);
        giftRid.current = null;
      }
      // 수령인은 한 번만 추가해, 주문이 일부 실패해 재시도할 때 중복으로 생기지 않게 한다.
      // 재시도 전에 정보를 고쳤으면 지웠다 다시 넣지 않고 수정으로 반영한다.
      const giftInfo = { name: giftName, address: giftAddr, phone: giftPhone, postal_code: giftPostal };
      const snapshot = JSON.stringify(giftInfo);
      if (gift && !giftRid.current) {
        const r = await addRecipient(project.id, giftInfo);
        giftRid.current = r.id; giftSent.current = snapshot;
      } else if (gift && giftRid.current && snapshot !== giftSent.current) {
        await patchRecipient(giftRid.current, giftInfo);
        giftSent.current = snapshot;
      }
      const res = await createOrder(project.id, { name, phone, postalCode: postal, address });
      setDone(res);
    } catch (e) { setError(e instanceof Error ? e.message : "주문에 실패했어요"); } finally { setBusy(false); }
  };

  if (done) return (
    <div style={{ padding: "76px var(--gut)" }}>
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
    <div style={{ padding: "76px var(--gut) 120px" }}>
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
          <div className="g-book" aria-hidden="true" />
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
        <span>{spec ? `${spec.name} ${copies}권` : `책 ${copies}권`}</span>
        <b>{subtotal === null ? "—" : won(subtotal)}</b>
      </div>
      <p className="ship-note">배송비는 결제 단계에서 계산돼요</p>

      {error && <p className="error-text">{error}</p>}
      <div className="bottom-bar">
        <button className="btn" style={{ width: "100%" }} disabled={busy} onClick={submit}>
          {busy ? "책을 만드는 중…" : subtotal === null ? "주문하기" : `주문하기 · ${won(subtotal)}`}
        </button>
      </div>
    </div>
  );
}
