/** 여행 중 순간 담기: 이미 만든 여행에 사진+녹음+감정을 계속 추가한다. 앨범의 "＋"에서 온다.
 *  누가 호출: App 라우터(/p/:id/add).
 *  무엇을 호출: api(getProject), components/MomentCapture. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, type Project } from "../api";
import MomentCapture from "../components/MomentCapture";

export default function AddMoments() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState<Project | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => { getProject(id).then(setP).catch(() => setFailed(true)); }, [id]);
  if (failed) return (
    <div style={{ padding: 80, textAlign: "center", color: "var(--soft)" }}>
      <p>여행을 불러오지 못했어요.</p>
      <button className="btn-ghost" onClick={() => nav("/")}>← 서재로</button>
    </div>
  );
  if (!p) return <div style={{ padding: 80, textAlign: "center", color: "var(--soft)" }}>여는 중…</div>;

  return (
    <div style={{ minHeight: "100dvh", paddingBottom: 40 }}>
      <div className="cap-header">
        <button className="backbtn" onClick={() => nav(`/p/${id}`)} aria-label="여행 앨범으로">←</button>
        <div><p className="cap-kick">{(p.title || "TRIP").toUpperCase()}</p><h1>순간 담기</h1></div>
      </div>
      <div style={{ padding: "0 var(--gut)" }}>
        <MomentCapture projectId={id} initialMoments={p.photos} />
      </div>
    </div>
  );
}
