/** 새 여행 만들기 + 순간 담기: 제목 → 사진 추가 → 사진마다 목소리 녹음(자동 업로드→캡션) + 감정 탭.
 *  누가 호출: App 라우터(/new).
 *  무엇을 호출: api(createProject/uploadPhotos/uploadAudio/patchMoment/getAnalysis), lib/library(addTrip). */
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, uploadPhotos, uploadAudio, patchMoment, getAnalysis, photoImageUrl, type Moment } from "../api";
import { addTrip } from "../lib/library";
import Recorder from "../components/Recorder";

const EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"];

export default function NewTrip() {
  const nav = useNavigate();
  const [pid, setPid] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [companions, setCompanions] = useState("");
  const [moments, setMoments] = useState<Moment[]>([]);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const ensureProject = async (): Promise<string> => {
    if (pid) return pid;
    if (!title.trim()) { setError("여행 제목을 적어주세요"); throw new Error("no title"); }
    const { id } = await createProject({ title, companions: companions || undefined });
    addTrip(id); setPid(id); return id;
  };

  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    try {
      const id = await ensureProject();
      const { photos } = await uploadPhotos(id, [...files]);
      setMoments((cur) => [...cur, ...photos]);
    } catch (e) { if (e instanceof Error && e.message !== "no title") setError(e.message); }
  };

  const onAudio = async (m: Moment, blob: Blob) => {
    const id = pid ?? (await ensureProject());
    await uploadAudio(m.id, blob);
    // 캡션 생성 폴링(이 순간만): analysis_status done/failed까지 (audio 올린 순간에만)
    const poll = setInterval(async () => {
      const p = await getAnalysis(id);
      const s = p.photos.find((x) => x.id === m.id);
      if (s && (s.analysis_status === "done" || s.analysis_status === "failed")) {
        clearInterval(poll);
        setMoments((cur) => cur.map((x) => (x.id === m.id ? { ...x, caption: s.caption, analysis_status: s.analysis_status } : x)));
      }
    }, 2000);
  };

  const setEmotion = (m: Moment, e: string) => {
    patchMoment(m.id, { emotion: e });
    setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, emotion: e } : x));
  };

  return (
    <div style={{ padding: "24px 20px 100px" }}>
      <input placeholder="여행 제목 — 예: 제주, 봄" value={title} onChange={(e) => setTitle(e.target.value)}
        style={{ font: "800 22px/1.3 var(--sans)", border: 0, background: "transparent", width: "100%", outline: "none", padding: 0 }} />
      <input placeholder="함께한 사람 (선택)" value={companions} onChange={(e) => setCompanions(e.target.value)}
        style={{ border: 0, borderBottom: "1px solid var(--line)", background: "transparent", width: "100%", padding: "8px 0", marginTop: 8, borderRadius: 0 }} />

      <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e) => onFiles(e.target.files)} />
      <button className="btn-ghost" style={{ margin: "18px 0" }} onClick={() => fileRef.current?.click()}>＋ 사진 담기</button>

      {moments.map((m) => (
        <div key={m.id} className="capture-card">
          <img className="capture-thumb" src={photoImageUrl(m.id)} alt="" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <Recorder onRecorded={(b) => onAudio(m, b)} />
            {m.analysis_status === "done" && m.caption && <p className="capture-cap">“{m.caption}”</p>}
            {m.analysis_status === "pending" && m.caption == null && <p className="capture-cap muted">녹음하면 여기에 글귀가 생겨요</p>}
            <div className="emotions">
              {EMOTIONS.map((e) => (
                <button key={e} className={"emotion" + (m.emotion === e ? " on" : "")} onClick={() => setEmotion(m, e)}>{e}</button>
              ))}
            </div>
          </div>
        </div>
      ))}

      {error && <p className="error-text">{error}</p>}
      {moments.length > 0 && (
        <div className="bottom-bar">
          <button className="btn" style={{ width: "100%" }} onClick={() => nav(`/p/${pid}`)}>여행 앨범 열기</button>
        </div>
      )}
    </div>
  );
}
