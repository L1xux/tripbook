/** 순간 카드: 풀블리드 사진 + 탭하면 글귀 시트(A 하단 슬라이드업) + 감정 칩 + 음성 파형 + 필름 날짜 스탬프.
 *  누가 호출: screens/Album(덱).
 *  무엇을 호출: api(photoImageUrl/audioUrl), components/AudioWaveform. */
import { useState } from "react";
import AudioWaveform from "./AudioWaveform";
import { photoImageUrl, audioUrl, type Moment } from "../api";

export default function MomentCard({ m, stamp }: { m: Moment; index: number; stamp: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={"card" + (open ? " open" : "")} style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}
      onClick={() => setOpen((o) => !o)}>
      {m.emotion && <span className="chip">{m.emotion}</span>}
      {!open && <div className="taphint">탭하면 그때 내 말이 떠올라요</div>}
      <div className="sheet">
        <p className="q">{m.caption ?? m.transcript ?? "아직 목소리가 없는 순간"}</p>
        {m.has_audio && (
          <div className="voice"><AudioWaveform src={audioUrl(m.id)} autoplay={open} /><span className="lab">내 목소리</span><span className="st">{stamp}</span></div>
        )}
      </div>
    </div>
  );
}
