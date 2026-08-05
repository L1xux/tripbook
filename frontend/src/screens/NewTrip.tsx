/** 새 여행 만들기. 제목과 동행자를 받아 여행을 만들고 바로 순간 담기로 넘어간다.
 *  App 라우터의 /new에서 열린다.
 *  api의 createProject와 lib/library의 addTrip, components/MomentCapture를 쓴다. */
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
    <div style={{ minHeight: "100dvh", paddingBottom: 100 }}>
      <div className="cap-header">
        <button className="backbtn" onClick={() => nav("/")} aria-label="서재로">←</button>
      </div>
      <div className="newtrip-body">
        <p className="cap-kick">새 여행</p>
        <h1 className="newtrip-q">이번 여행을<br />무엇이라 부를까요?</h1>
        <input className="newtrip-title" placeholder="예: 제주, 봄" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input className="newtrip-with" placeholder="함께한 사람 (선택)" value={companions} onChange={(e) => setCompanions(e.target.value)} />
        {error && <p className="error-text">{error}</p>}
        <p className="newtrip-hint">제목을 정하면, 다음 화면에서 사진과 그때의 목소리로 순간을 담아요.</p>
      </div>
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
        <button className="btn-ghost" onClick={() => nav("/")}>완료</button>
      </div>
      <div style={{ padding: "0 var(--gut)" }}>
        <MomentCapture projectId={pid} initialMoments={[]} />
      </div>
    </div>
  );
}
