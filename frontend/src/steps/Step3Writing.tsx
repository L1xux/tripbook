/** 위자드 3단계: 집필 실시간 피드. 완성된 페이지가 책 페이지로 하나씩 조판되어
 * 사용자는 기다리는 게 아니라 읽는다 (설계서 §3 실시간 페이지 피드). */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, writeStreamUrl, type Page } from "../api";
import Wizard from "../Wizard";

type FeedEvent =
  | { type: "page"; id: string; page_number: number; photo_id: string | null; text: string }
  | { type: "done" } | { type: "error"; message: string };

export default function Step3Writing() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [pages, setPages] = useState<Page[]>([]);
  const [photoCount, setPhotoCount] = useState(0);
  const [state, setState] = useState<"writing" | "done" | "error">("writing");
  const [errMsg, setErrMsg] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let es: EventSource | null = null;
    // 새로고침 대비: 이미 저장된 페이지 먼저 로드하고, 끝난 집필이면 스트림을 열지 않는다
    getProject(id).then((p) => {
      setPages(p.pages);
      setPhotoCount(p.photos.length);
      if (p.status === "ready") { setState("done"); return; }
      es = new EventSource(writeStreamUrl(id));
      es.onmessage = (e) => {
        const ev: FeedEvent = JSON.parse(e.data);
        if (ev.type === "page") {
          setPages((cur) => [...cur.filter((p) => p.id !== ev.id),
            { id: ev.id, page_number: ev.page_number, photo_id: ev.photo_id, text: ev.text, regen_count: 0 }]);
        } else if (ev.type === "done") { setState("done"); es?.close(); }
        else { setState("error"); setErrMsg(ev.message); es?.close(); }
      };
    });
    return () => es?.close();
  }, [id]);

  // 새 페이지가 조판되면 그 페이지로 시선을 옮긴다
  useEffect(() => {
    if (state === "writing" && pages.length > 0)
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [pages.length, state]);

  const ordered = [...pages].sort((a, b) => a.page_number - b.page_number); // state를 변이하지 않게 복사 후 정렬
  const placed = ordered.filter((p) => p.photo_id).length;
  // 예상 분량: 사진 페이지 전부 + 프롤로그/에필로그 몫. 어림값이므로 "약"을 붙인다
  const expected = photoCount + 2;
  const ratio = Math.min(ordered.length / expected, 1);

  return (
    <Wizard step="writing">
      <h2>{state === "done" ? "원고가 완성되었어요" : "지금, 여행기가 써지고 있어요"}</h2>

      {state !== "error" && (
        <div style={{ margin: "14px 0 6px" }}>
          <div className="progress-rule"><i style={{ width: `${ratio * 100}%` }} /></div>
          <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
            {ordered.length}쪽 완성 · 사진 {photoCount}장 중 {placed}장 배치
            {state === "writing" && ` · 약 ${expected}쪽 예상`}
          </p>
        </div>
      )}

      {ordered.map((p) => (
        <article key={p.id} className="book-page">
          <p className="marker">{p.photo_id ? "사진이 들어갈 자리" : "글로만 쓰인 페이지"}</p>
          <p className="body">{p.text}</p>
          <p className="folio">NO.{String(p.page_number).padStart(2, "0")}</p>
        </article>
      ))}

      {state === "writing" && (
        <p className="writing-now">
          <span className="ink-cursor" aria-hidden="true" />
          {pages.length === 0 ? "작가가 첫 문장을 고르고 있어요" : `${pages.length + 1}쪽을 쓰는 중`}
        </p>
      )}
      {state === "error" && (
        <div className="notice">
          <p className="error-text">{errMsg}</p>
          <button className="btn-ghost" onClick={() => nav(`/p/${id}/photos`)}>사진 단계로 돌아가기</button>
        </div>
      )}
      <div ref={endRef} />

      {state === "done" && (
        <div className="bottom-bar">
          <button className="btn-primary" onClick={() => nav(`/p/${id}/review`)}>
            다 읽었어요, 퇴고하러 가기
          </button>
        </div>
      )}
    </Wizard>
  );
}
