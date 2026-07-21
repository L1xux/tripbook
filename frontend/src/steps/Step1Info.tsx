/** 위자드 1단계: 여행 정보 + 무드 선택. 제출하면 프로젝트를 만들고 2단계로. */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, type Mood } from "../api";

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

  const submit = async () => {
    if (!title.trim()) return alert("여행 제목을 입력해주세요");
    setBusy(true);
    try {
      const { id } = await createProject({
        title, mood, start_date: start || undefined, end_date: end || undefined,
        companions: companions || undefined,
      });
      nav(`/p/${id}/photos`);
    } finally { setBusy(false); }
  };

  return (
    <div>
      <h1>Tripbook</h1>
      <p style={{ color: "#6b6558", margin: "4px 0 16px" }}>
        여행 사진과 몇 줄의 메모가, 한 권의 이야기가 됩니다
      </p>
      <label>여행 제목</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 제주 봄 여행" />
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <div style={{ flex: 1 }}><label>시작일</label>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></div>
        <div style={{ flex: 1 }}><label>종료일</label>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></div>
      </div>
      <div style={{ marginTop: 12 }}><label>동행</label>
        <input value={companions} onChange={(e) => setCompanions(e.target.value)} placeholder="예: 엄마, 동생" /></div>
      <h3 style={{ marginTop: 20 }}>어떤 이야기로 만들까요?</h3>
      {MOODS.map((m) => (
        <div key={m.value} className="card" onClick={() => setMood(m.value)}
          style={{ borderColor: mood === m.value ? "#2c6e63" : undefined, cursor: "pointer" }}>
          <strong>{m.label}</strong>
          <p style={{ fontSize: 13, color: "#6b6558" }}>{m.desc}</p>
        </div>
      ))}
      <div className="bottom-bar">
        <button className="btn-primary" onClick={submit} disabled={busy}>
          {busy ? "만드는 중..." : "여행 만들기"}
        </button>
      </div>
    </div>
  );
}
