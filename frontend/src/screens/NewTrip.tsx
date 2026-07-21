/** 새 여행 만들기: 제목/동행자 입력 → 여행 생성 → 순간 담기(MomentCapture 공용).
 *  누가 호출: App 라우터(/new).
 *  무엇을 호출: api(createProject), lib/library(addTrip), components/MomentCapture. */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject } from "../api";
import { addTrip } from "../lib/library";
import MomentCapture from "../components/MomentCapture";

export default function NewTrip() {
  const nav = useNavigate();
  const [pid, setPid] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [companions, setCompanions] = useState("");
  const [error, setError] = useState("");

  const start = async () => {
    if (!title.trim()) { setError("여행 제목을 적어주세요"); return; }
    try {
      const { id } = await createProject({ title, companions: companions || undefined });
      addTrip(id); setPid(id); setError("");
    } catch (e) { setError(e instanceof Error ? e.message : "여행을 만들지 못했어요"); }
  };

  if (!pid) return (
    <div style={{ padding: "24px 20px 100px" }}>
      <input placeholder="여행 제목 — 예: 제주, 봄" value={title} onChange={(e) => setTitle(e.target.value)}
        style={{ font: "800 22px/1.3 var(--sans)", border: 0, background: "transparent", width: "100%", outline: "none", padding: 0 }} />
      <input placeholder="함께한 사람 (선택)" value={companions} onChange={(e) => setCompanions(e.target.value)}
        style={{ border: 0, borderBottom: "1px solid var(--line)", background: "transparent", width: "100%", padding: "8px 0", marginTop: 8, borderRadius: 0 }} />
      {error && <p className="error-text">{error}</p>}
      <div className="bottom-bar">
        <button className="btn" style={{ width: "100%" }} onClick={start}>여행 시작하기</button>
      </div>
    </div>
  );

  return (
    <div style={{ minHeight: "100dvh", paddingBottom: 40 }}>
      <div className="cap-header">
        <button className="backbtn" onClick={() => nav("/")} aria-label="서재로">←</button>
        <h1 style={{ flex: 1 }}>{title}</h1>
        <button className="btn-ghost" onClick={() => nav(`/p/${pid}`)}>앨범 →</button>
      </div>
      <div style={{ padding: "0 20px" }}>
        <MomentCapture projectId={pid} initialMoments={[]} />
      </div>
    </div>
  );
}
