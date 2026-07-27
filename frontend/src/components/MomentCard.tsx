/** 순간 카드: 풀블리드 사진 + 탭하면 글귀 시트(A 하단 슬라이드업) + 감정 칩 + 음성 파형 + 필름 날짜 스탬프.
 *  목소리가 없는 순간은 카드에서 바로 녹음해 담을 수 있다.
 *  누가 호출: screens/Album(덱).
 *  무엇을 호출: api(photoImageUrl/audioUrl/uploadAudio/getAnalysis), components/AudioWaveform·Recorder. */
import { useEffect, useRef, useState } from "react";
import AudioWaveform from "./AudioWaveform";
import Recorder from "./Recorder";
import { photoImageUrl, audioUrl, uploadAudio, getAnalysis, type Moment } from "../api";

export default function MomentCard({ m, projectId, stamp, onUpdate }:
  { m: Moment; index: number; stamp: { name: string; no: string }; projectId: string; onUpdate: (patch: Partial<Moment>) => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const timers = useRef<number[]>([]);
  useEffect(() => () => { timers.current.forEach(clearInterval); }, []);

  // 카드에서 바로 목소리를 담는다 — 업로드 즉시 파형이 뜨고, 전사가 끝나면 글귀로 채워진다
  const onAudio = async (blob: Blob) => {
    setBusy(true);
    try { await uploadAudio(m.id, blob); }
    catch { setBusy(false); return; }
    onUpdate({ has_audio: true, analysis_status: "processing" });
    let tries = 0;
    const poll = window.setInterval(async () => {
      if (++tries > 30) { clearInterval(poll); setBusy(false); onUpdate({ analysis_status: "failed" }); return; }
      const p = await getAnalysis(projectId);
      const s = p.photos.find((x) => x.id === m.id);
      if (s && (s.analysis_status === "done" || s.analysis_status === "failed")) {
        clearInterval(poll); setBusy(false);
        onUpdate({ caption: s.caption, transcript: s.transcript, analysis_status: s.analysis_status });
      }
    }, 2000);
    timers.current.push(poll);
  };

  const processing = busy || m.analysis_status === "processing";
  const line = m.caption ?? m.transcript ?? (processing ? "목소리를 글귀로 옮기는 중…" : "아직 목소리가 없는 순간");
  return (
    <div className={"card" + (open ? " open" : "")} style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}
      onClick={() => setOpen((o) => !o)}>
      {m.emotion && <span className="chip">{m.emotion}</span>}
      {!open && <div className="taphint">{m.has_audio ? "탭하면 그때 내 말이 떠올라요" : "탭해서 목소리를 담아요"}</div>}
      <div className="sheet">
        <p className="q">{line}</p>
        {m.has_audio ? (
          <div className="voice"><AudioWaveform src={audioUrl(m.id)} bars={24} autoplay={open} /><span className="lab">내 목소리</span>
            <span className="st"><span className="st-ko">{stamp.name}</span><span className="st-no">{stamp.no}</span></span></div>
        ) : (
          <div className="voice-add" onClick={(e) => e.stopPropagation()}>
            <Recorder onRecorded={onAudio} busy={processing} />
          </div>
        )}
      </div>
    </div>
  );
}
