/** 위자드 1단계: 여행 정보 + 무드 선택. 제출하면 프로젝트를 만들고 2단계로. */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, type Mood } from "../api";
import Wizard from "../Wizard";

const MOODS: { value: Mood; label: string; desc: string }[] = [
  { value: "family_essay", label: "따뜻한 가족 에세이", desc: "사소한 순간에서 의미를 찾는 회고" },
  { value: "friendship_saga", label: "유쾌한 우정 무용담", desc: "두고두고 놀릴 수 있는 유머" },
  { value: "fantasy_adventure", label: "판타지 모험기", desc: "여행을 모험담으로 각색" },
  { value: "lyrical_essay", label: "서정적 여행 에세이", desc: "감각 묘사 중심의 차분한 문체" },
  { value: "comedy", label: "유쾌한 코미디", desc: "어이없음과 반전을 살리는 경쾌함" },
];

export default function Step1Info() {
  const nav = useNavigate();
  const [title, setTitle] = useState("");
  const [mood, setMood] = useState<Mood>("family_essay");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [companions, setCompanions] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (!title.trim()) return setError("여행 제목을 적어주세요 — 책의 표지가 됩니다");
    setError("");
    setBusy(true);
    try {
      const { id } = await createProject({
        title, mood, start_date: start || undefined, end_date: end || undefined,
        companions: companions || undefined,
      });
      nav(`/p/${id}/photos`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "잠시 후 다시 시도해주세요");
    } finally { setBusy(false); }
  };

  return (
    <Wizard step="info">
      <p className="eyebrow">여행이 한 권의 책이 됩니다</p>
      <h1>어떤 여행이었나요</h1>
      <p className="muted" style={{ marginTop: 6 }}>
        사진과 몇 줄의 메모만 있으면, 나머지는 작가가 씁니다.
      </p>

      <label htmlFor="t-title">여행 제목</label>
      <input id="t-title" value={title} onChange={(e) => setTitle(e.target.value)}
        placeholder="제주, 봄의 기록" />

      <div style={{ display: "flex", gap: 20 }}>
        <div style={{ flex: 1 }}>
          <label htmlFor="t-start">시작일</label>
          <input id="t-start" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </div>
        <div style={{ flex: 1 }}>
          <label htmlFor="t-end">종료일</label>
          <input id="t-end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </div>
      </div>

      <label htmlFor="t-comp">함께한 사람</label>
      <input id="t-comp" value={companions} onChange={(e) => setCompanions(e.target.value)}
        placeholder="엄마, 동생" />

      <h2 style={{ marginTop: 36 }}>어떤 이야기로 쓸까요</h2>
      <p className="muted">문체를 고르면 책 전체의 목소리가 정해집니다.</p>
      <div style={{ marginTop: 8 }}>
        {MOODS.map((m) => (
          <button key={m.value} type="button"
            className={"mood" + (mood === m.value ? " on" : "")}
            onClick={() => setMood(m.value)} aria-pressed={mood === m.value}>
            <strong>{m.label}</strong>
            <p>{m.desc}</p>
          </button>
        ))}
      </div>

      {error && <p className="error-text" role="alert">{error}</p>}
      <div className="bottom-bar">
        <button className="btn-primary" onClick={submit} disabled={busy}>
          {busy ? "책을 펴는 중…" : "이 여행으로 시작하기"}
        </button>
      </div>
    </Wizard>
  );
}
