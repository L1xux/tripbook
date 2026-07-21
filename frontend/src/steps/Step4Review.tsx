/** 위자드 4단계: 페이지별 직접 수정 + 피드백 재생성. 인쇄물은 사용자가 최종 확인한다. */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, patchPage, regeneratePage, type Page } from "../api";
import { patchById } from "../utils";
import Wizard from "../Wizard";

export default function Step4Review() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [pages, setPages] = useState<Page[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [feedbackFor, setFeedbackFor] = useState<string | null>(null); // 피드백 입력이 열린 페이지
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { getProject(id).then((p) => setPages(p.pages)); }, [id]);

  const save = async (pageId: string, text: string) => {
    await patchPage(pageId, text);
    setPages((cur) => patchById(cur, pageId, { text }));
  };

  const openFeedback = (pageId: string) => {
    setFeedbackFor(feedbackFor === pageId ? null : pageId);
    setFeedback("");
  };

  const regen = async (pageId: string) => {
    if (!feedback.trim()) return;
    setBusyId(pageId);
    setError("");
    try {
      const res = await regeneratePage(pageId, feedback.trim());
      setPages((cur) => patchById(cur, pageId, { text: res.text, regen_count: res.regen_count }));
      setFeedbackFor(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "다시 시도해주세요");
    } finally { setBusyId(null); }
  };

  return (
    <Wizard step="review">
      <h2>마음에 들 때까지 다듬어요</h2>
      <p className="muted">본문을 눌러 직접 고치거나, 작가에게 다시 부탁할 수 있어요.</p>

      {pages.map((p) => (
        <article key={p.id} className="book-page">
          <p className="marker">
            {p.photo_id ? "사진이 들어갈 자리" : "글로만 쓰인 페이지"}
            {p.regen_count > 0 && ` · ${p.regen_count}번 고쳐 씀`}
          </p>
          <textarea rows={6} defaultValue={p.text} key={p.text} aria-label={`${p.page_number}쪽 본문`}
            onBlur={(e) => e.target.value !== p.text && save(p.id, e.target.value)} />
          <p className="folio">NO.{String(p.page_number).padStart(2, "0")}</p>

          <div style={{ textAlign: "right" }}>
            <button className="btn-line" onClick={() => openFeedback(p.id)}>
              {feedbackFor === p.id ? "닫기" : "작가에게 다시 부탁하기"}
            </button>
          </div>
          {feedbackFor === p.id && (
            <div className="feedback-row">
              <input autoFocus value={feedback} onChange={(e) => setFeedback(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && regen(p.id)}
                placeholder="예: 더 웃기게, 엄마 이야기를 넣어서" />
              <button className="btn-ghost" onClick={() => regen(p.id)} disabled={busyId === p.id}>
                {busyId === p.id ? "쓰는 중…" : "부탁"}
              </button>
            </div>
          )}
        </article>
      ))}

      {error && <p className="error-text" role="alert">{error}</p>}
      <div className="bottom-bar">
        <button className="btn-primary" onClick={() => nav(`/p/${id}/order`)}>
          이대로 좋아요, 책으로 만들기
        </button>
      </div>
    </Wizard>
  );
}
