/** 순간 담기(공용): 사진 추가 + 사진마다 목소리 녹음(자동 캡션) + 감정 탭. 새 여행/기존 여행 모두 이걸 쓴다.
 *  누가 호출: screens/NewTrip(새 여행), screens/AddMoments(여행 중 추가).
 *  무엇을 호출: api(uploadPhotos/uploadAudio/patchMoment/getAnalysis/photoImageUrl), components/Recorder. */
import { useEffect, useRef, useState } from "react";
import { uploadPhotos, uploadAudio, patchMoment, deleteMoment, getAnalysis, photoImageUrl, type Moment } from "../api";
import Recorder from "./Recorder";
import Camera from "./Camera";

const EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"];

export default function MomentCapture({ projectId, initialMoments }: { projectId: string; initialMoments: Moment[] }) {
  const [moments, setMoments] = useState<Moment[]>(initialMoments);
  const [error, setError] = useState("");
  const [camOpen, setCamOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  // 열린 폴링 인터벌을 추적해 언마운트 시 모두 정리한다(화면 이탈 후에도 백엔드를 계속 때리는 것 방지)
  const timers = useRef<number[]>([]);
  useEffect(() => () => { timers.current.forEach(clearInterval); timers.current = []; }, []);

  // 사진 업로드 후 AI 비전이 감정 후보(suggested_emotion)를 채우면 화면에 반영한다(짧게 폴링)
  const pollSuggestions = (ids: string[]) => {
    let tries = 0;
    const poll = window.setInterval(async () => {
      // 종료 판정을 요청보다 먼저 — 백엔드가 죽어 getAnalysis가 계속 던지면 인터벌이 영원히 안 멈춘다
      if (++tries > 6) { clearInterval(poll); return; }
      try {
        const p = await getAnalysis(projectId);
        setMoments((cur) => cur.map((x) => {
          const s = p.photos.find((y) => y.id === x.id);
          return s?.suggested_emotion ? { ...x, suggested_emotion: s.suggested_emotion } : x;
        }));
        if (ids.every((id) => p.photos.find((y) => y.id === id)?.suggested_emotion)) clearInterval(poll);
      } catch { /* 다음 틱에 재시도, tries가 상한 */ }
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
    e.target.value = "";  // 리셋해야 같은 파일을 다시 골라도 change가 발화한다(삭제 후 재선택)
  };

  const onAudio = async (m: Moment, blob: Blob) => {
    // 녹음 직후 즉시 "처리 중" 표시 — 반응이 없으면 됐는지 알 수 없다
    setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, has_audio: true, analysis_status: "processing" } : x));
    try { await uploadAudio(m.id, blob); }
    catch {
      setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, has_audio: false, analysis_status: "pending" } : x));
      setError("목소리를 올리지 못했어요"); return;
    }
    // 캡션 생성 폴링(이 순간만): done/failed까지 — 최대 시도 제한 + 언마운트 정리
    let tries = 0;
    const poll = window.setInterval(async () => {
      // 분석이 끝나지 않아도 60초(30회) 후엔 멈추고 실패로 표시(무한 폴링·무한 로딩 방지)
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
      } catch { /* 일시 오류면 다음 틱에 재시도, tries가 상한 */ }
    }, 2000);
    timers.current.push(poll);
  };

  const setEmotion = (m: Moment, e: string) => {
    const prev = m.emotion;  // PATCH 실패 시 되돌릴 이전 값
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
      const prev = m.caption;  // PATCH 실패 시 되돌릴 이전 캡션
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
            {!m.emotion && m.suggested_emotion && <p className="ai-hint">✨ AI가 이 순간을 “{m.suggested_emotion}”으로 봤어요 — 탭해서 선택</p>}
            <div className="emotions">
              {EMOTIONS.map((e) => {
                const on = m.emotion === e;
                const suggested = !m.emotion && m.suggested_emotion === e;
                return (
                  <button key={e} className={"emotion" + (on ? " on" : "") + (suggested ? " suggested" : "")} onClick={() => setEmotion(m, e)}>
                    {suggested ? "✨ " : ""}{e}
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
