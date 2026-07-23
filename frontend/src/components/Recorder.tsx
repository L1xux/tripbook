/** 목소리 한 마디 녹음 버튼(MediaRecorder). 누르면 녹음, 다시 누르면 정지→onRecorded(blob).
 *  누가 호출: screens/NewTrip(사진마다 하나).
 *  무엇을 호출: navigator.mediaDevices, MediaRecorder. */
import { useEffect, useRef, useState } from "react";

export default function Recorder({ onRecorded, busy }: { onRecorded: (b: Blob) => void; busy?: boolean }) {
  const [rec, setRec] = useState(false);
  const [sec, setSec] = useState(0);
  const mr = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<number | null>(null);
  const stream = useRef<MediaStream | null>(null);

  // 녹음 중 화면을 벗어나면(뒤로가기/완료) 마이크가 계속 켜진 채 남는다 — 언마운트 시 반드시 정리
  useEffect(() => () => {
    stream.current?.getTracks().forEach((t) => t.stop());
    if (timer.current) clearInterval(timer.current);
  }, []);

  const start = async () => {
    const s = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.current = s;
    const m = new MediaRecorder(s);
    chunks.current = [];
    m.ondataavailable = (e) => chunks.current.push(e.data);
    m.onstop = () => { onRecorded(new Blob(chunks.current, { type: m.mimeType || "audio/webm" })); s.getTracks().forEach((t) => t.stop()); };
    m.start(); mr.current = m; setRec(true); setSec(0);
    timer.current = window.setInterval(() => setSec((x) => x + 1), 1000);
  };
  const stop = () => { mr.current?.stop(); setRec(false); if (timer.current) clearInterval(timer.current); };

  // 녹음이 끝나고 글귀로 옮기는 동안(busy)엔 다시 녹음하지 못하게 막는다
  // — 반복 녹음이 무음 전사를 부르던 원인을 차단
  return (
    <button type="button" className={rec ? "rec on" : "rec"} disabled={!!busy && !rec}
      onClick={() => (rec ? stop() : start())}>
      {rec ? `● ${sec}s · 탭해서 멈추기` : busy ? "목소리 담는 중…" : "🎙️ 목소리로 한 마디"}
    </button>
  );
}
