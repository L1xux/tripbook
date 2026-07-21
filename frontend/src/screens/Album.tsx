/** 앨범: 카드 덱(스와이프) ⇄ ▦ 전체 그리드. 덱 끝엔 "책으로 만들기" 카드(Task 5).
 *  누가 호출: App 라우터(/p/:id).
 *  무엇을 호출: api(getProject/photoImageUrl), components/MomentCard. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, photoImageUrl, type Project } from "../api";
import MomentCard from "../components/MomentCard";
import BookPreview from "../components/BookPreview";
import OrderSheet from "../components/OrderSheet";

export default function Album() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState<Project | null>(null);
  const [idx, setIdx] = useState(0);
  const [view, setView] = useState<"deck" | "grid" | "book" | "order">("deck");

  useEffect(() => { getProject(id).then(setP); }, [id]);
  if (!p) return <div style={{ padding: 80, textAlign: "center", color: "var(--soft)" }}>여는 중…</div>;

  const M = p.photos;
  const stamp = (i: number) => `${(p.title || "TRIP").toUpperCase().slice(0, 6)} · ${String(i + 1).padStart(2, "0")}`;
  const atEnd = idx >= M.length;

  if (view === "grid") return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => setView("deck")}>‹ {p.title}</span><span className="ic on" onClick={() => setView("deck")}>▦</span></div>
      <div className="gwrap">
        {M.map((m, i) => (
          <button key={m.id} className="cell" style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}
            onClick={() => { setIdx(i); setView("deck"); }} />
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
      <OrderSheet project={p} />
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
      <div className="deck">
        {atEnd ? (
          <div className="endcard">
            <div className="kick">{(p.title || "").toUpperCase()}</div>
            <h3>{M.length}개의 순간</h3>
            <p>여기까지가 이 여행이에요. 이대로 한 권의 책이 되면, 언제든 다시 펼쳐볼 수 있어요.</p>
            <button className="btn" onClick={() => setView("book")}>책으로 만들기</button>
            <button className="btn-ghost" onClick={() => setIdx(M.length - 1)}>← 순간 더 보기</button>
          </div>
        ) : (
          <MomentCard key={M[idx].id} m={M[idx]} index={idx} stamp={stamp(idx)} />
        )}
      </div>
      {!atEnd && (
        <>
          <span className="nav prev" onClick={() => setIdx((i) => Math.max(0, i - 1))}>‹</span>
          <span className="nav next" onClick={() => setIdx((i) => Math.min(M.length, i + 1))}>›</span>
          <div className="dots">{M.map((_, i) => <i key={i} className={i === idx ? "on" : ""} />)}</div>
        </>
      )}
    </div>
  );
}
