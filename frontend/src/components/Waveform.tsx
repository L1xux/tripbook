/** 시그니처: 앰버 음성 파형. 실제 오디오 분석 없이 결정적 막대 패턴(순간 id 시드)으로 그린다.
 *  누가 호출: components/MomentCard.
 *  무엇을 호출: (없음) — 순수 프레젠테이션. */
export default function Waveform({ seed = 0, playing = false }: { seed?: number; playing?: boolean }) {
  const bars = Array.from({ length: 16 }, (_, i) => 5 + Math.round(15 * Math.abs(Math.sin((i + seed) * 1.3))));
  return (
    <span className="wave" aria-hidden>
      {bars.map((h, i) => <i key={i} style={{ height: h, animationDelay: `${i * 0.06}s` }} className={playing ? "on" : ""} />)}
    </span>
  );
}
