/** 위자드 2단계: 사진+메모 입력. 업로드 즉시 AI 분석이 백그라운드로 돌고,
 * 완료된 분석은 "AI가 본 장면"으로 카드에 떠서 탭하면 그 자리에서 교정할 수 있다. */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getAnalysis, getProject, patchPhoto, photoImageUrl, reorderPhotos,
  startWriting, uploadPhotos, type Photo,
} from "../api";
import { patchById } from "../utils";
import Wizard from "../Wizard";

const EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"];

export default function Step2Photos() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [editingScene, setEditingScene] = useState<string | null>(null); // 교정 중인 photo id
  const [sceneDraft, setSceneDraft] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
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

  const openSceneEdit = (p: Photo) => {
    setEditingScene(p.id);
    setSceneDraft(scene(p) ?? "");
  };
  const commitSceneEdit = (photoId: string) => {
    if (sceneDraft.trim()) savePhoto(photoId, { user_scene_correction: sceneDraft.trim() });
    setEditingScene(null);
  };

  const go = async () => {
    if (!photos.length) return setError("사진을 한 장 이상 담아주세요");
    setBusy(true);
    try {
      await startWriting(id);
      nav(`/p/${id}/writing`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "잠시 후 다시 시도해주세요");
      setBusy(false);
    }
  };

  return (
    <Wizard step="photos">
      <h2>사진과 기억을 담아주세요</h2>
      <p className="muted">사진 한 장이 책의 한 페이지가 됩니다. 순서가 곧 이야기의 순서예요.</p>

      <input ref={fileRef} type="file" accept="image/*" multiple hidden
        onChange={(e) => onFiles(e.target.files)} />
      <div style={{ margin: "18px 0 4px" }}>
        <button className="btn-ghost" onClick={() => fileRef.current?.click()}>
          + 사진 담기
        </button>
        {photos.length > 0 && (
          <span className="muted" style={{ marginLeft: 12, fontSize: 13 }}>{photos.length}장</span>
        )}
      </div>

      {photos.length === 0 && (
        <p className="notice">아직 담긴 사진이 없어요. 여행 순서대로 골라 담으면 정리가 쉬워요.</p>
      )}

      {photos.map((p, i) => (
        <div key={p.id} className="photo-card">
          <img className="photo-thumb" src={photoImageUrl(p.id)} alt={`${i + 1}번째 사진`} />
          <div className="photo-body">
            <div className="photo-meta">
              <span>CUT {String(i + 1).padStart(2, "0")}</span>
              <span className="order-btns">
                <button onClick={() => move(i, -1)} aria-label="앞으로">↑</button>
                <button onClick={() => move(i, 1)} aria-label="뒤로">↓</button>
              </span>
            </div>

            <p className="photo-scene">
              {p.analysis_status === "pending" && <span className="hint">작가가 사진을 살펴보는 중…</span>}
              {p.analysis_status === "failed" && <span className="hint">사진을 읽지 못했어요 — 메모가 그 몫을 대신합니다</span>}
              {p.analysis_status === "done" && editingScene !== p.id && (
                <>
                  {scene(p)}{" "}
                  <button className="btn-line" onClick={() => openSceneEdit(p)}>고치기</button>
                </>
              )}
            </p>
            {editingScene === p.id && (
              <div className="feedback-row">
                <input autoFocus value={sceneDraft} onChange={(e) => setSceneDraft(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && commitSceneEdit(p.id)}
                  placeholder="이 장면을 한 문장으로" />
                <button className="btn-ghost" onClick={() => commitSceneEdit(p.id)}>저장</button>
              </div>
            )}

            <div className="emotions">
              {EMOTIONS.map((e) => (
                <button key={e} className={"emotion" + (p.emotion === e ? " on" : "")}
                  onClick={() => savePhoto(p.id, { emotion: e })} aria-pressed={p.emotion === e}>
                  {e}
                </button>
              ))}
            </div>

            <textarea rows={2} placeholder="그때의 기억을 두어 줄로"
              defaultValue={p.note ?? ""}
              onBlur={(e) => savePhoto(p.id, { note: e.target.value })} />
          </div>
        </div>
      ))}

      {error && <p className="error-text" role="alert">{error}</p>}
      <div className="bottom-bar">
        <button className="btn-primary" onClick={go} disabled={busy}>
          {busy ? "작가에게 원고를 넘기는 중…" : "작가에게 집필 맡기기"}
        </button>
      </div>
    </Wizard>
  );
}
