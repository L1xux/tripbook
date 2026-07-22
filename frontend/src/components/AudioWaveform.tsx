/** 시그니처: 진짜 음성 파형 + 재생. 오디오를 Web Audio로 디코드해 진폭 막대를 그리고, 탭하면 재생/진행 표시.
 *  누가 호출: MomentCard, screens/Voice.
 *  무엇을 호출: fetch(src) + AudioContext.decodeAudioData + <audio>. */
import { useEffect, useRef, useState } from "react";

export default function AudioWaveform({ src, bars = 32, autoplay }: { src: string; bars?: number; autoplay?: boolean }) {
  const [peaks, setPeaks] = useState<number[]>([]);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // 카드가 열리면(autoplay=true) 자동 재생 — "탭하면 그때 내 말이 떠올라요"의 실제 동작.
  // autoplay를 넘기지 않는 화면(공개 /v/:id)에선 기존처럼 파형 탭으로만 재생한다.
  useEffect(() => {
    const a = audioRef.current;
    if (!a || autoplay === undefined) return;
    if (autoplay) void a.play().catch(() => { /* 자동재생 차단 시 파형 탭으로 재생 */ });
    else { a.pause(); a.currentTime = 0; }
  }, [autoplay]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(src);
        if (!res.ok) return;
        const buf = await res.arrayBuffer();
        const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const ctx = new AC();
        try {
          const decoded = await ctx.decodeAudioData(buf);
          const data = decoded.getChannelData(0);
          const block = Math.floor(data.length / bars) || 1;
          const out: number[] = [];
          for (let i = 0; i < bars; i++) {
            let sum = 0;
            for (let j = 0; j < block; j++) sum += Math.abs(data[i * block + j] || 0);
            out.push(sum / block);
          }
          const max = Math.max(...out, 1e-4);
          if (!cancelled) setPeaks(out.map((v) => v / max));
        } finally {
          ctx.close();  // 디코드 실패(예: Safari의 webm)해도 컨텍스트를 반드시 닫아 누수 방지
        }
      } catch { /* 폴백 정적 막대 사용 */ }
    })();
    return () => { cancelled = true; };
  }, [src, bars]);

  const shown = peaks.length ? peaks : Array.from({ length: bars }, (_, i) => 0.35 + 0.4 * Math.abs(Math.sin(i)));
  const active = Math.floor(progress * shown.length);
  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    const a = audioRef.current; if (!a) return;
    if (playing) a.pause(); else void a.play();
  };

  return (
    <span className="wave" onClick={toggle} role="button" aria-label={playing ? "일시정지" : "재생"}>
      {shown.map((h, i) => (
        <i key={i} style={{ height: 5 + Math.round(17 * h) }} className={playing && i <= active ? "on" : ""} />
      ))}
      <audio ref={audioRef} src={src} preload="none"
        onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
        onEnded={() => { setPlaying(false); setProgress(0); }}
        onTimeUpdate={(e) => { const a = e.currentTarget; setProgress(a.duration ? a.currentTime / a.duration : 0); }} />
    </span>
  );
}
