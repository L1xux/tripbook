/** 여행 중 바로 찍는 카메라. 라이브 화면을 띄우고 셔터를 누르면 JPEG 파일로 넘긴다.
 *  components/MomentCapture가 쓴다.
 *  navigator.mediaDevices.getUserMedia와 canvas를 쓴다. */
import { useEffect, useRef, useState } from "react";

export default function Camera({ onCapture, onClose }: { onCapture: (f: File) => void; onClose: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = s;
        if (videoRef.current) { videoRef.current.srcObject = s; void videoRef.current.play(); }
      })
      .catch(() => setErr("카메라를 열 수 없어요. 브라우저 권한을 확인해주세요."));
    return () => { streamRef.current?.getTracks().forEach((t) => t.stop()); };
  }, []);

  const shoot = () => {
    const v = videoRef.current; if (!v || !v.videoWidth) return;
    const cv = document.createElement("canvas");
    cv.width = v.videoWidth; cv.height = v.videoHeight;
    cv.getContext("2d")!.drawImage(v, 0, 0);
    cv.toBlob((b) => {
      if (!b) return;
      onCapture(new File([b], `shot-${Date.now()}.jpg`, { type: "image/jpeg" }));
      onClose();
    }, "image/jpeg", 0.92);
  };

  return (
    <div className="camera">
      {err ? <p className="camera-err">{err}</p> : <video ref={videoRef} playsInline muted className="camera-view" />}
      <div className="camera-bar">
        <button className="btn-ghost" onClick={onClose}>닫기</button>
        {!err && <button className="shutter" aria-label="촬영" onClick={shoot} />}
        <span style={{ width: 64 }} />
      </div>
    </div>
  );
}
