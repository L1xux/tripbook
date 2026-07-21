/** 공개 재생 페이지(인쇄 QR 목적지): 사진 + 명조 글귀 + 진짜 파형으로 그때 목소리를 다시 듣는다.
 *  누가 호출: App 라우터(/v/:id).
 *  무엇을 호출: api(getMoment/photoImageUrl/audioUrl), components/AudioWaveform. */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getMoment, photoImageUrl, audioUrl, type PublicMoment } from "../api";
import AudioWaveform from "../components/AudioWaveform";

export default function Voice() {
  const { id = "" } = useParams();
  const [m, setM] = useState<PublicMoment | "loading" | "missing">("loading");
  useEffect(() => { getMoment(id).then(setM).catch(() => setM("missing")); }, [id]);
  if (m === "loading") return <div className="voice-empty">여는 중…</div>;
  if (m === "missing") return <div className="voice-empty">이 순간은 더 이상 없어요.</div>;
  return (
    <div className="voice-page" style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}>
      <div className="voice-sheet">
        {m.emotion && <span className="chip">{m.emotion}</span>}
        <p className="q">{m.caption ?? m.transcript ?? "그때의 목소리"}</p>
        {m.has_audio && (
          <div className="voice">
            <AudioWaveform src={audioUrl(m.id)} /><span className="lab">그때 목소리</span><span className="st">{m.project_title}</span>
          </div>
        )}
      </div>
    </div>
  );
}
