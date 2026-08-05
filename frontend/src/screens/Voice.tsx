/** 인쇄된 QR이 가리키는 공개 페이지. 사진과 글귀, 파형으로 그때 목소리를 다시 듣는다.
 *  App 라우터의 /v/:id에서 열린다.
 *  api의 getMoment와 audioUrl, components/AudioWaveform을 쓴다. */
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
        <p className="voice-eyebrow">{m.project_title}</p>
        {m.emotion && <span className="chip">{m.emotion}</span>}
        <p className="q">{m.caption ?? m.transcript ?? "그때의 목소리"}</p>
        {m.has_audio ? (
          <div className="voice voice-play">
            <AudioWaveform src={audioUrl(m.id)} bars={24} withButton />
            <span className="lab">그때 목소리 듣기</span>
          </div>
        ) : (
          <p className="voice-none">이 순간엔 목소리가 담기지 않았어요.</p>
        )}
      </div>
    </div>
  );
}
