/** 위자드 2단계: 사진+메모 입력. 업로드 즉시 AI 분석이 백그라운드로 돌고,
 * 완료된 분석은 "AI가 본 장면"으로 카드에 떠서 탭하면 교정할 수 있다. */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getAnalysis, getProject, patchPhoto, reorderPhotos, startWriting, uploadPhotos, type Photo } from "../api";
import { patchById } from "../utils";

const EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"];

export default function Step2Photos() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { getProject(id).then((p) => setPhotos(p.photos)); }, [id]);

  // 분석 폴링: pending이 남아있는 동안 2초마다.
  // 왜 boolean에만 의존하는가: photos 배열에 의존하면 틱마다 인터벌이 재생성된다
  const hasPending = photos.some((p) => p.analysis_status === "pending");
  useEffect(() => {
    if (!hasPending) return;
    const t = setInterval(async () => {
      const { photos: st } = await getAnalysis(id);
      setPhotos((cur) => {
        let changed = false;
        const next = cur.map((p) => {
          const s = st.find((x) => x.id === p.id);
          if (s && (s.analysis_status !== p.analysis_status || s.scene !== p.scene)) {
            changed = true;
            return { ...p, analysis_status: s.analysis_status, scene: s.scene };
          }
          return p;
        });
        return changed ? next : cur; // 변화 없으면 참조 유지 → 불필요한 리렌더 방지
      });
    }, 2000);
    return () => clearInterval(t);
  }, [id, hasPending]);

  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    // 업로드 응답이 새 사진 목록을 이미 담고 있다 — getProject 재요청 불필요
    const { photos: added } = await uploadPhotos(id, [...files]);
    setPhotos((cur) => [...cur.filter((p) => !added.some((a) => a.id === p.id)), ...added]);
  };

  const move = async (idx: number, dir: -1 | 1) => {
    const next = [...photos];
    const j = idx + dir;
    if (j < 0 || j >= next.length) return;
    [next[idx], next[j]] = [next[j], next[idx]];
    setPhotos(next);
    await reorderPhotos(id, next.map((p) => p.id));
  };

  /** 서버 PATCH + 낙관적 로컬 반영을 한 쌍으로 묶는다. */
  const savePhoto = (photoId: string, patch: Partial<Pick<Photo, "note" | "emotion" | "user_scene_correction">>) => {
    patchPhoto(photoId, patch);
    setPhotos((cur) => patchById(cur, photoId, patch));
  };

  const scene = (p: Photo) => p.user_scene_correction ?? p.scene;

  const go = async () => {
    if (!photos.length) return alert("사진을 올려주세요");
    await startWriting(id);
    nav(`/p/${id}/writing`);
  };

  return (
    <div>
      <h2>사진과 기억을 담아주세요</h2>
      <input ref={fileRef} type="file" accept="image/*" multiple hidden
        onChange={(e) => onFiles(e.target.files)} />
      <button className="btn-primary" style={{ margin: "12px 0" }}
        onClick={() => fileRef.current?.click()}>사진 추가</button>
      {photos.map((p, i) => (
        <div key={p.id} className="card">
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
            <span>#{i + 1}</span>
            <span>
              <button onClick={() => move(i, -1)}>↑</button>{" "}
              <button onClick={() => move(i, 1)}>↓</button>
            </span>
          </div>
          <p style={{ fontSize: 13, color: "#2c6e63", margin: "6px 0" }}>
            {p.analysis_status === "pending" && "🔍 AI가 사진을 보는 중..."}
            {p.analysis_status === "failed" && "분석 실패 — 메모만으로 진행합니다"}
            {p.analysis_status === "done" && (
              <span onClick={() => {
                const fix = prompt("AI가 본 장면을 고쳐주세요", scene(p) ?? "");
                if (fix) savePhoto(p.id, { user_scene_correction: fix });
              }}>💬 AI가 본 장면: {scene(p)} ✏️</span>
            )}
          </p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "6px 0" }}>
            {EMOTIONS.map((e) => (
              <button key={e} onClick={() => savePhoto(p.id, { emotion: e })}
                style={{ borderRadius: 999, padding: "4px 10px", fontSize: 13,
                  border: "1px solid #d8d3c8",
                  background: p.emotion === e ? "#2c6e63" : "#fff",
                  color: p.emotion === e ? "#fff" : "#232323" }}>{e}</button>
            ))}
          </div>
          <textarea rows={2} placeholder="그때의 기억을 2~3줄로 적어주세요"
            defaultValue={p.note ?? ""}
            onBlur={(e) => savePhoto(p.id, { note: e.target.value })} />
        </div>
      ))}
      <div className="bottom-bar">
        <button className="btn-primary" onClick={go}>AI에게 집필 맡기기 ✍️</button>
      </div>
    </div>
  );
}
