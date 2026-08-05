/** 사진을 담고 순간마다 목소리를 녹음해 글귀를 만들고 감정을 고른다. 새 여행과 기존 여행이 함께 쓴다.
 *  누가 호출: screens의 NewTrip과 AddMoments.
 *  무엇을 호출: api의 업로드와 조회 함수, components의 Recorder와 Camera. */
import { useEffect, useRef, useState } from "react";
import { uploadPhotos, uploadAudio, patchMoment, deleteMoment, getAnalysis, photoImageUrl, type Moment } from "../api";
import Recorder from "./Recorder";
import Camera from "./Camera";

const EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"];

// 감정 제안은 AI가 판별했다고 말하지 않고 순간이 말을 거는 것으로 표현한다.
// 사용자의 순간을 분석 대상으로 만들지 않기 위해서다.
// 받침이 있으면 "이라고", 없으면 "라고"를 붙여 감정 태그가 늘어나도 어색해지지 않게 한다.
const saidAs = (w: string) => {
  const code = w.charCodeAt(w.length - 1) - 0xac00;
  const hasFinalConsonant = code >= 0 && code <= 11171 && code % 28 !== 0;
  return `“${w}”${hasFinalConsonant ? "이" : ""}라고`;
};

export default function MomentCapture({ projectId, initialMoments }: { projectId: string; initialMoments: Moment[] }) {
  const [moments, setMoments] = useState<Moment[]>(initialMoments);
  const [error, setError] = useState("");
  const [camOpen, setCamOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  // 화면을 떠난 뒤에도 백엔드를 계속 부르지 않도록 열린 폴링을 모아 두고 언마운트 때 정리한다
  const timers = useRef<number[]>([]);
  useEffect(() => () => { timers.current.forEach(clearInterval); timers.current = []; }, []);

  // 사진을 올린 뒤 감정 후보가 채워지면 화면에 반영한다
  const pollSuggestions = (ids: string[]) => {
    let tries = 0;
    const poll = window.setInterval(async () => {
      // 종료 판정을 요청보다 먼저 한다. 백엔드가 죽어 요청이 계속 실패해도 폴링이 멈추게 하기 위해서다.
      if (++tries > 6) { clearInterval(poll); return; }
      try {
        const p = await getAnalysis(projectId);
        setMoments((cur) => cur.map((x) => {
          const s = p.photos.find((y) => y.id === x.id);
          return s?.suggested_emotion ? { ...x, suggested_emotion: s.suggested_emotion } : x;
        }));
        if (ids.every((id) => p.photos.find((y) => y.id === id)?.suggested_emotion)) clearInterval(poll);
      } catch { /* 다음 차례에 다시 시도하고, 횟수가 상한이 된다 */ }
    }, 2500);
    timers.current.push(poll);
  };

  const addFiles = async (files: File[]) => {
    if (!files.length) return;
    try {
      const { photos } = await uploadPhotos(projectId, files);
      setMoments((cur) => [...cur, ...photos]);
      pollSuggestions(photos.map((p) => p.id));
    } catch (e) { setError(e instanceof Error ? e.message : "사진을 올리지 못했어요"); }
  };
  const onFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files?.length) void addFiles([...files]);
    e.target.value = "";  // 값을 비워야 같은 파일을 다시 골랐을 때도 change가 발생한다
  };

  const onAudio = async (m: Moment, blob: Blob) => {
    // 녹음 직후 바로 처리 중을 보여준다. 반응이 없으면 됐는지 알 수 없다.
    setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, has_audio: true, analysis_status: "processing" } : x));
    try { await uploadAudio(m.id, blob); }
    catch {
      setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, has_audio: false, analysis_status: "pending" } : x));
      setError("목소리를 올리지 못했어요"); return;
    }
    // 이 순간의 글귀가 만들어질 때까지 폴링한다. 시도 횟수를 제한하고 언마운트 때 정리한다.
    let tries = 0;
    const poll = window.setInterval(async () => {
      // 60초가 지나면 멈추고 실패로 표시해, 화면이 영원히 로딩에 머물지 않게 한다
      if (++tries > 30) {
        clearInterval(poll);
        setMoments((cur) => cur.map((x) => x.id === m.id && x.analysis_status === "processing" ? { ...x, analysis_status: "failed" } : x));
        return;
      }
      try {
        const p = await getAnalysis(projectId);
        const s = p.photos.find((x) => x.id === m.id);
        if (s && (s.analysis_status === "done" || s.analysis_status === "failed")) {
          clearInterval(poll);
          setMoments((cur) => cur.map((x) => (x.id === m.id ? { ...x, caption: s.caption, analysis_status: s.analysis_status } : x)));
        }
      } catch { /* 일시적인 오류면 다음 차례에 다시 시도한다 */ }
    }, 2000);
    timers.current.push(poll);
  };

  const setEmotion = (m: Moment, e: string) => {
    const prev = m.emotion;  // 저장에 실패하면 되돌릴 값
    setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, emotion: e } : x));
    patchMoment(m.id, { emotion: e }).catch(() => {
      setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, emotion: prev } : x));
      setError("감정을 저장하지 못했어요");
    });
  };

  const removeMoment = (m: Moment) => {
    if (!confirm("이 순간을 삭제할까요?")) return;
    deleteMoment(m.id).then(() => setMoments((cur) => cur.filter((x) => x.id !== m.id)));
  };

  const startEdit = (m: Moment) => { setEditing(m.id); setDraft(m.caption ?? ""); };
  const saveEdit = (m: Moment) => {
    const v = draft.trim();
    setEditing(null);
    if (v && v !== m.caption) {
      const prev = m.caption;  // 저장에 실패하면 되돌릴 글귀
      setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, caption: v } : x));
      patchMoment(m.id, { caption: v }).catch(() => {
        setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, caption: prev } : x));
        setError("글귀를 저장하지 못했어요");
      });
    }
  };

  return (
    <>
      <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={onFiles} />
      <p className="capture-lead">사진을 담고, <b>그때의 목소리로</b><br />한 마디 남겨요.</p>
      <div style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        <button className="btn" style={{ flex: 1, padding: "13px" }} onClick={() => setCamOpen(true)}>📷 카메라로 찍기</button>
        <button className="btn-ghost" onClick={() => fileRef.current?.click()}>＋ 갤러리</button>
      </div>
      {camOpen && <Camera onCapture={(f) => void addFiles([f])} onClose={() => setCamOpen(false)} />}

      {moments.map((m) => (
        <div key={m.id} className="capture-card">
          <div className="capture-photo">
            <img className="capture-thumb" src={photoImageUrl(m.id)} alt="" />
            <button className="cap-del" onClick={() => removeMoment(m)} aria-label="순간 삭제">×</button>
          </div>
          <div className="capture-body">
            <Recorder onRecorded={(b) => onAudio(m, b)} busy={m.analysis_status === "processing"} />
            {editing === m.id ? (
              <textarea className="cap-edit" value={draft} autoFocus
                onChange={(e) => setDraft(e.target.value)} onBlur={() => saveEdit(m)} />
            ) : m.analysis_status === "processing" ? (
              <p className="capture-cap busy">🖊️ 목소리를 글귀로 옮기는 중…</p>
            ) : m.caption ? (
              <p className="capture-cap" onClick={() => startEdit(m)} title="탭해서 수정">“{m.caption}”</p>
            ) : m.has_audio && m.analysis_status === "done" ? (
              <p className="capture-cap muted">목소리를 알아듣지 못했어요. 다시 한 번 담아볼까요?</p>
            ) : (
              <p className="capture-cap muted">녹음하면 여기에 글귀가 생겨요</p>
            )}
            {!m.emotion && m.suggested_emotion && (
              <p className="ai-hint">이 순간은 {saidAs(m.suggested_emotion)} 말하는 것 같아요 — 탭해서 담기</p>
            )}
            <div className="emotions">
              {EMOTIONS.map((e) => {
                const on = m.emotion === e;
                const suggested = !m.emotion && m.suggested_emotion === e;
                return (
                  <button key={e} className={"emotion" + (on ? " on" : "") + (suggested ? " suggested" : "")} onClick={() => setEmotion(m, e)}>
                    {suggested ? `‘${e}’` : e}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ))}

      {error && <p className="error-text">{error}</p>}
    </>
  );
}
