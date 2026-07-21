/** 위자드 4단계: 페이지별 직접 수정 + 피드백 재생성. 인쇄물은 사용자가 최종 확인한다. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, patchPage, regeneratePage, type Page } from "../api";

export default function Step4Review() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [pages, setPages] = useState<Page[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => { getProject(id).then((p) => setPages(p.pages)); }, [id]);

  const save = async (pageId: string, text: string) => {
    await patchPage(pageId, text);
    setPages((cur) => cur.map((p) => (p.id === pageId ? { ...p, text } : p)));
  };

  const regen = async (pageId: string) => {
    const feedback = prompt("어떻게 다시 쓸까요? (예: 더 웃기게, 엄마 얘기를 넣어줘)");
    if (!feedback) return;
    setBusyId(pageId);
    try {
      const res = await regeneratePage(pageId, feedback);
      setPages((cur) => cur.map((p) => (p.id === pageId ? { ...p, text: res.text, regen_count: res.regen_count } : p)));
    } finally { setBusyId(null); }
  };

  return (
    <div>
      <h2>마음에 들 때까지 다듬어요</h2>
      {pages.map((p) => (
        <div key={p.id} className="card">
          <span style={{ fontSize: 12, color: "#6b6558" }}>
            {p.page_number}p {p.photo_id ? "📷" : "✒️"}
          </span>
          <textarea rows={6} defaultValue={p.text} key={p.text}
            onBlur={(e) => e.target.value !== p.text && save(p.id, e.target.value)} />
          <button onClick={() => regen(p.id)} disabled={busyId === p.id}
            style={{ marginTop: 6, fontSize: 13 }}>
            {busyId === p.id ? "다시 쓰는 중..." : "🔄 AI에게 다시 써달라기"}
          </button>
        </div>
      ))}
      <div className="bottom-bar">
        <button className="btn-primary" onClick={() => nav(`/p/${id}/order`)}>
          이대로 좋아요, 책으로 만들기 📖
        </button>
      </div>
    </div>
  );
}
