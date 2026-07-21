/** 위자드 3단계: 집필 실시간 피드. 완성된 페이지가 카드로 하나씩 추가되어
 * 사용자는 기다리는 게 아니라 읽는다 (설계서 §3 실시간 페이지 피드). */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, writeStreamUrl, type Page } from "../api";

type FeedEvent =
  | { type: "page"; id: string; page_number: number; photo_id: string | null; text: string }
  | { type: "done" } | { type: "error"; message: string };

export default function Step3Writing() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [pages, setPages] = useState<Page[]>([]);
  const [state, setState] = useState<"writing" | "done" | "error">("writing");
  const [errMsg, setErrMsg] = useState("");

  useEffect(() => {
    // 새로고침 대비: 이미 저장된 페이지 먼저 로드
    getProject(id).then((p) => {
      setPages(p.pages);
      if (p.status === "ready") setState("done");
    });
    const es = new EventSource(writeStreamUrl(id));
    es.onmessage = (e) => {
      const ev: FeedEvent = JSON.parse(e.data);
      if (ev.type === "page") {
        setPages((cur) => [...cur.filter((p) => p.id !== ev.id),
          { id: ev.id, page_number: ev.page_number, photo_id: ev.photo_id, text: ev.text, regen_count: 0 }]);
      } else if (ev.type === "done") { setState("done"); es.close(); }
      else { setState("error"); setErrMsg(ev.message); es.close(); }
    };
    return () => es.close();
  }, [id]);

  return (
    <div>
      <h2>여행기가 써지고 있어요</h2>
      {pages.sort((a, b) => a.page_number - b.page_number).map((p) => (
        <div key={p.id} className="card">
          <span style={{ fontSize: 12, color: "#6b6558" }}>
            {p.page_number}p {p.photo_id ? "📷" : "✒️"}
          </span>
          <p style={{ marginTop: 6, lineHeight: 1.7 }}>{p.text}</p>
        </div>
      ))}
      {state === "writing" && <p style={{ color: "#2c6e63" }}>✍️ 다음 페이지를 쓰는 중...</p>}
      {state === "error" && <p style={{ color: "#b3423a" }}>{errMsg}</p>}
      {state === "done" && (
        <div className="bottom-bar">
          <button className="btn-primary" onClick={() => nav(`/p/${id}/review`)}>
            다 읽었어요, 퇴고하러 가기
          </button>
        </div>
      )}
    </div>
  );
}
