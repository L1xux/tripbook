/** 앨범: 카드 덱(스와이프) ⇄ ▦ 전체 그리드. 덱 끝엔 "책으로 만들기" 카드(Task 5).
 *  누가 호출: App 라우터(/p/:id).
 *  무엇을 호출: api(getProject/photoImageUrl), components/MomentCard. */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, generateArc, reorderMoments, photoImageUrl, type Project } from "../api";
import MomentCard from "../components/MomentCard";
import BookPreview from "../components/BookPreview";
import OrderSheet from "../components/OrderSheet";
import OrderStatus from "../components/OrderStatus";

export default function Album() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState<Project | null>(null);
  const [idx, setIdx] = useState(0);
  const [view, setView] = useState<"deck" | "grid" | "book" | "order" | "status">("deck");
  const [arcBusy, setArcBusy] = useState(false);
  const [reorder, setReorder] = useState(false);
  const [pick, setPick] = useState<number | null>(null);
  const drag = useRef<number | null>(null);
  const swiped = useRef(false);

  useEffect(() => { getProject(id).then(setP); }, [id]);

  const makeArc = async () => {
    setArcBusy(true);
    try { const r = await generateArc(id); setP((prev) => prev ? { ...prev, emotion_arc: r.arc } : prev); }
    finally { setArcBusy(false); }
  };
  if (!p) return <div style={{ padding: 80, textAlign: "center", color: "var(--soft)" }}>여는 중…</div>;

  const M = p.photos;
  const stamp = (i: number) => `${(p.title || "TRIP").toUpperCase().slice(0, 6)} · ${String(i + 1).padStart(2, "0")}`;
  const atEnd = idx >= M.length;
  const goPrev = () => setIdx((i) => Math.max(0, i - 1));
  const goNext = () => setIdx((i) => Math.min(M.length, i + 1));
  const doMove = (from: number, to: number) => {
    const arr = [...M]; const [it] = arr.splice(from, 1); arr.splice(to, 0, it);
    setP((prev) => prev ? { ...prev, photos: arr } : prev);
    reorderMoments(id, arr.map((x) => x.id));
  };

  if (view === "grid") return (
    <div className="album-screen light">
      <div className="bar dark">
        <span onClick={() => setView("deck")}>‹ {p.title}</span>
        <span className="ic" style={{ fontSize: 13, color: reorder ? "var(--stamp)" : "var(--ink)" }}
          onClick={() => { setReorder((r) => !r); setPick(null); }}>{reorder ? "완료" : "순서 편집"}</span>
      </div>
      {reorder && <p className="reorder-hint">옮길 순간을 탭하고, 놓을 자리를 탭하세요</p>}
      <div className="gwrap">
        {M.map((m, i) => (
          <button key={m.id} className={"cell" + (pick === i ? " picked" : "")} style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}
            onClick={() => {
              if (!reorder) { setIdx(i); setView("deck"); return; }
              if (pick === null) setPick(i);
              else { if (pick !== i) doMove(pick, i); setPick(null); }
            }} />
        ))}
      </div>
    </div>
  );

  if (view === "book") return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => setView("deck")}>‹ 미리보기</span></div>
      <BookPreview project={p} onOrder={() => setView("order")} />
    </div>
  );
  if (view === "order") return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => setView("book")}>‹ 주문</span></div>
      <OrderSheet project={p} onViewStatus={() => { getProject(id).then(setP); setView("status"); }} />
    </div>
  );
  if (view === "status") return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => setView("deck")}>‹ {p.title}</span></div>
      <OrderStatus projectId={id} />
    </div>
  );

  return (
    <div className="album-screen dark">
      <div className="bar light">
        <span onClick={() => nav("/")}>‹ {p.title}</span>
        <span style={{ display: "flex", gap: 10 }}>
          <span className="ic" onClick={() => nav(`/p/${id}/add`)} aria-label="순간 담기">＋</span>
          <span className="ic" onClick={() => setView("grid")}>▦</span>
        </span>
      </div>
      {!atEnd && <span className="counter">{String(idx + 1).padStart(2, "0")} / {String(M.length).padStart(2, "0")}</span>}
      <div className="deck"
        onPointerDown={(e) => { drag.current = e.clientX; swiped.current = false; }}
        onPointerMove={(e) => { if (drag.current !== null && Math.abs(e.clientX - drag.current) > 12) swiped.current = true; }}
        onPointerUp={(e) => { const d = drag.current; drag.current = null; if (d !== null) { const dx = e.clientX - d; if (Math.abs(dx) > 50) (dx < 0 ? goNext() : goPrev()); } }}
        onClickCapture={(e) => { if (swiped.current) { e.stopPropagation(); swiped.current = false; } }}>
        {atEnd ? (
          <div className="endcard">
            <div className="kick">{(p.title || "").toUpperCase()}</div>
            <h3>{M.length}개의 순간</h3>
            {p.emotion_arc
              ? <p className="arc">“{p.emotion_arc}”</p>
              : <p>여기까지가 이 여행이에요. 이대로 한 권의 책이 되면, 언제든 다시 펼쳐볼 수 있어요.</p>}
            <button className="btn" onClick={() => setView("book")}>책으로 만들기</button>
            {p.order_status && <button className="btn-ghost" onClick={() => setView("status")}>주문 현황 보기</button>}
            {!p.emotion_arc && M.length > 0 && (
              <button className="btn-ghost" onClick={makeArc} disabled={arcBusy}>{arcBusy ? "요약하는 중…" : "✨ 이 여행 감정 요약"}</button>
            )}
            <button className="btn-ghost" onClick={() => setIdx(M.length - 1)}>← 순간 더 보기</button>
          </div>
        ) : (
          <MomentCard key={M[idx].id} m={M[idx]} index={idx} stamp={stamp(idx)} />
        )}
      </div>
      {!atEnd && (
        <>
          <span className="nav prev" onClick={goPrev}>‹</span>
          <span className="nav next" onClick={goNext}>›</span>
          <div className="dots">{M.map((_, i) => <i key={i} className={i === idx ? "on" : ""} />)}</div>
        </>
      )}
    </div>
  );
}
