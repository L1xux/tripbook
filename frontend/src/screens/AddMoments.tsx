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

  useEffect(() => { getProject(id).then(setP); }, [id]);
  if (!p) return <div style={{ padding: 80, textAlign: "center", color: "var(--soft)" }}>여는 중…</div>;

  return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => nav(`/p/${id}`)}>‹ {p.title}</span></div>
      <div style={{ padding: "62px 20px 40px" }}>
        <h1 style={{ font: "800 22px/1.3 var(--sans)", letterSpacing: "-.02em" }}>순간 담기</h1>
        <MomentCapture projectId={id} initialMoments={p.photos} />
      </div>
    </div>
  );
}
