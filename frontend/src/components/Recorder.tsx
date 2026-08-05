/** 목소리 한 마디를 녹음하는 버튼. 누르면 녹음하고 다시 누르면 멈춰 결과를 넘긴다.
 *  MomentCapture와 MomentCard가 쓴다.
 *  navigator.mediaDevices와 MediaRecorder를 쓴다. */
import { useEffect, useRef, useState } from "react";

export default function Recorder({ onRecorded, busy }: { onRecorded: (b: Blob) => void; busy?: boolean }) {
  const [rec, setRec] = useState(false);
  const [sec, setSec] = useState(0);
  const [err, setErr] = useState("");
  const mr = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<number | null>(null);
  const stream = useRef<MediaStream | null>(null);

  // 녹음 중 화면을 벗어나면 마이크가 켜진 채 남으므로 언마운트 때 반드시 정리한다
  useEffect(() => () => {
    stream.current?.getTracks().forEach((t) => t.stop());
    if (timer.current) clearInterval(timer.current);
  }, []);

  const start = async () => {
    let s: MediaStream;
    try {
      s = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      // 권한이 거부되거나 마이크가 없을 때 조용히 넘기면 버튼이 안 눌리는 것처럼 보인다
      setErr("마이크를 열 수 없어요. 브라우저 권한을 확인해주세요.");
      return;
    }
    setErr("");
    stream.current = s;
    const m = new MediaRecorder(s);
    chunks.current = [];
    m.ondataavailable = (e) => chunks.current.push(e.data);
    m.onstop = () => { onRecorded(new Blob(chunks.current, { type: m.mimeType || "audio/webm" })); s.getTracks().forEach((t) => t.stop()); };
    m.start(); mr.current = m; setRec(true); setSec(0);
    timer.current = window.setInterval(() => setSec((x) => x + 1), 1000);
  };
  const stop = () => { mr.current?.stop(); setRec(false); if (timer.current) clearInterval(timer.current); };

  // 글귀로 옮기는 동안에는 다시 녹음하지 못하게 막는다. 반복 녹음이 무음 전사를 부르던 원인이다.
  return (
    <>
      <button type="button" className={rec ? "rec on" : "rec"} disabled={!!busy && !rec}
        onClick={() => (rec ? stop() : start())}>
        {rec ? `● ${sec}s · 탭해서 멈추기` : busy ? "목소리 담는 중…" : "🎙️ 목소리로 한 마디"}
      </button>
      {err && <p className="error-text" style={{ margin: "6px 0 0", fontSize: 12 }}>{err}</p>}
    </>
  );
}
