/** 목소리 한 마디 녹음 버튼(MediaRecorder). 누르면 녹음, 다시 누르면 정지→onRecorded(blob).
 *  누가 호출: screens/NewTrip(사진마다 하나).
 *  무엇을 호출: navigator.mediaDevices, MediaRecorder. */
import { useRef, useState } from "react";

export default function Recorder({ onRecorded }: { onRecorded: (b: Blob) => void }) {
  const [rec, setRec] = useState(false);
  const [sec, setSec] = useState(0);
  const mr = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<number | null>(null);

  const start = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const m = new MediaRecorder(stream);
    chunks.current = [];
    m.ondataavailable = (e) => chunks.current.push(e.data);
    m.onstop = () => { onRecorded(new Blob(chunks.current, { type: m.mimeType || "audio/webm" })); stream.getTracks().forEach((t) => t.stop()); };
    m.start(); mr.current = m; setRec(true); setSec(0);
    timer.current = window.setInterval(() => setSec((s) => s + 1), 1000);
  };
  const stop = () => { mr.current?.stop(); setRec(false); if (timer.current) clearInterval(timer.current); };

  return (
    <button type="button" className={rec ? "rec on" : "rec"} onClick={() => (rec ? stop() : start())}>
      {rec ? `● 녹음 중 ${sec}s — 탭해서 멈추기` : "🎙️ 목소리로 한 마디"}
    </button>
  );
}
