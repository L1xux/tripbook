/** 순간 담기(공용): 사진 추가 + 사진마다 목소리 녹음(자동 캡션) + 감정 탭. 새 여행/기존 여행 모두 이걸 쓴다.
 *  누가 호출: screens/NewTrip(새 여행), screens/AddMoments(여행 중 추가).
 *  무엇을 호출: api(uploadPhotos/uploadAudio/patchMoment/getAnalysis/photoImageUrl), components/Recorder. */
import { useRef, useState } from "react";
import { uploadPhotos, uploadAudio, patchMoment, getAnalysis, photoImageUrl, type Moment } from "../api";
import Recorder from "./Recorder";

const EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"];

export default function MomentCapture({ projectId, initialMoments }: { projectId: string; initialMoments: Moment[] }) {
  const [moments, setMoments] = useState<Moment[]>(initialMoments);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    try {
      const { photos } = await uploadPhotos(projectId, [...files]);
      setMoments((cur) => [...cur, ...photos]);
    } catch (e) { setError(e instanceof Error ? e.message : "사진을 올리지 못했어요"); }
  };

  const onAudio = async (m: Moment, blob: Blob) => {
    await uploadAudio(m.id, blob);
    setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, has_audio: true } : x));
    // 캡션 생성 폴링(이 순간만): audio 올린 순간에만, done/failed까지
    const poll = setInterval(async () => {
      const p = await getAnalysis(projectId);
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
    <>
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
    </>
  );
}
