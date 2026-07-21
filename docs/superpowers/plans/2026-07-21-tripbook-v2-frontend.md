# Tripbook v2 프론트엔드 (Voice Photobook UI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v1 위자드(무드→집필 SSE) 프론트엔드를, v2 백엔드(음성 캡션 포토북)에 맞춘 "서재 → 틴더 카드 덱 → 목소리 캡션 → 책 만들기·선물 주문" UI로 재구축한다. 비주얼은 확정된 필름/Retro 디자인(`design-v1.html`).

**Architecture:** React 19 + TypeScript + Vite. 계정 없음 — 서재 목록은 localStorage에 프로젝트 id를 보관. `api.ts` 한 곳으로만 v2 백엔드와 통신. 화면 3단: 홈(서재) → 앨범(카드 덱 ⇄ 그리드) → 순간(캡션+음성파형). 돈 흐름: 덱 끝 "책으로 만들기" 카드 → 책 펼침면 미리보기 → 주문+선물.

**Tech Stack:** React 19, TypeScript, Vite, react-router-dom, vitest, MediaRecorder(음성 녹음), EventSource 불필요(SSE 제거됨).

**Spec:** `docs/superpowers/specs/2026-07-21-tripbook-voice-photobook-design.md` (§3.5·3.6 디자인, §3 플로우)
**디자인 레퍼런스:** `.superpowers/brainstorm/*/content/design-v1.html` (색·타이포·인터랙션의 확정 목업 — 컴포넌트는 이걸 React로 옮기는 것)

## Global Constraints

- **디자인 토큰(§3.6):** 종이 `#F7F4EE`, 먹 `#191610`, 타우프 `#8C8578`, 라인 `#E7E1D6`, 필름 앰버 `#E4531F`(악센트—시그니처·주요액션에만). UI 산세리프(시스템), **글귀=명조 `Nanum Myeongjo`**, 날짜·쪽번호·카운터=`DM Mono`. 폰트는 Google Fonts로 로드.
- **시그니처:** 카드 탭 → 글귀가 명조로 조판 + **앰버 음성 파형** + 필름 날짜 스탬프.
- **화면 구조:** 홈(서재, 책장 진열) → 앨범 클릭 시 카드 덱(스와이프) ⇄ ▦ 전체 그리드 → 순간 탭 시 글귀(A 하단 슬라이드업 기본). 인쇄 캡션은 항상 A 스타일.
- **v2 API 계약(백엔드 구현 완료):**
  - `POST /api/v1/projects {title, start_date?, end_date?, companions?, cover_line?}` → `{id, title, status}`
  - `GET /api/v1/projects/{id}` → `{id,title,status,cover_line,reveal_mode,start_date,end_date,companions,order_status, photos:[MomentOut], recipients:[RecipientOut]}`
  - `MomentOut = {id, sort_order, emotion, note, caption, transcript, suggested_emotion, analysis_status}`
  - `POST /api/v1/projects/{id}/photos` (multipart `files`) → `{photos:[MomentOut]}` (202)
  - `GET /api/v1/photos/{id}/image` (썸네일 이미지)
  - `POST /api/v1/moments/{id}/audio` (multipart `file`) → 202 `{id, transcript_pending}`
  - `GET /api/v1/projects/{id}/photos/analysis` → `{photos:[{id, analysis_status, suggested_emotion, caption, transcript}]}`
  - `PATCH /api/v1/moments/{id} {emotion?, note?, caption?}` → `{ok}`
  - `PATCH /api/v1/projects/{id}/photos/order {photo_ids:[...]}` → `{ok}`
  - `POST /api/v1/projects/{id}/recipients {name, address, phone?, gift_message?}` → 201 `{id}`
  - `DELETE /api/v1/recipients/{rid}` → `{ok}`
  - `POST /api/v1/projects/{id}/order {spec, shipping}` → `{book_uid, orders:[{to, order_uid}]}` (사진 없으면 409)
  - `GET /api/v1/projects/{id}/order/status` → `{order_status, recipients:[{name, order_status}]}`
- `BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000"`.
- 라우트: `/`(서재), `/p/:id`(앨범—덱/그리드/순간/책/주문을 이 한 화면의 상태로 전환), `/new`(새 여행+담기).
- 검증: 각 태스크 후 `npm run build` 성공(타입체크 포함). api.ts는 `npm test`(vitest) 유닛테스트. 컴포넌트는 빌드 통과 + (가능하면) 스크린샷 확인.
- 커밋은 태스크마다 최소 1회, conventional commits.
- **⚠️ 백엔드 노트(Plan A에서 이월):** 음성 없는 순간은 `analysis_status`가 영원히 `"pending"`. 프론트는 "pending인데 audio 안 올린 순간"을 무한 로딩으로 표시하지 말 것 — 캡션 폴링은 audio를 올린 순간에 대해서만 건다.

---

### Task 1: API 클라이언트 v2 + 디자인 토큰 + 라우팅 셸

**Files:**
- Modify: `frontend/src/api.ts` (전체 교체), `frontend/src/index.css` (전체 교체), `frontend/src/App.tsx` (전체 교체), `frontend/index.html` (폰트 링크)
- Create: `frontend/src/lib/library.ts` (localStorage 서재 목록), `frontend/src/api.test.ts` (교체)
- Delete: `frontend/src/steps/*.tsx`, `frontend/src/Wizard.tsx`, `frontend/src/utils.ts`(patchById는 api.ts나 유지 판단)

**Interfaces:**
- Produces: `api.ts` 함수 — `createProject`, `getProject`, `uploadPhotos`, `photoImageUrl`, `uploadAudio`, `getAnalysis`, `patchMoment`, `reorderMoments`, `addRecipient`, `removeRecipient`, `createOrder`, `getOrderStatus`. 타입 `Moment`, `Recipient`, `Project`.
- Produces: `library.ts` — `listTrips(): string[]`, `addTrip(id: string)`, `removeTrip(id)`.

- [ ] **Step 1: 실패하는 테스트** — `frontend/src/api.test.ts` 전체 교체:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { createProject, uploadAudio } from "./api";

describe("api v2", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 201, json: async () => ({ id: "p1" }) })));
  });
  it("createProject posts title without mood", async () => {
    const res = await createProject({ title: "제주" });
    expect(res.id).toBe("p1");
    const [url, init] = (fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/projects");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).not.toHaveProperty("mood");
  });
  it("uploadAudio posts multipart to moments/{id}/audio", async () => {
    const blob = new Blob(["x"], { type: "audio/m4a" });
    await uploadAudio("m1", blob);
    const [url, init] = (fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/moments/m1/audio");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
  });
});
```
실행: `npm test` → FAIL (v2 함수 없음)

- [ ] **Step 2: api.ts 구현** — `frontend/src/api.ts` 전체 교체:
```typescript
/** 백엔드 v2 API 클라이언트. 모든 컴포넌트는 이 파일로만 서버와 통신한다. */
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let msg = `요청 실패 (${res.status})`;
    try { const b = await res.json(); if (typeof b.detail === "string") msg = b.detail; } catch { /* keep */ }
    throw new Error(msg);
  }
  return res.json();
}

export interface Moment { id: string; sort_order: number; emotion: string | null; note: string | null;
  caption: string | null; transcript: string | null; suggested_emotion: string | null; analysis_status: string; }
export interface Recipient { id: string; name: string; phone: string | null; address: string;
  gift_message: string | null; order_status: string | null; }
export interface Project { id: string; title: string; status: string; cover_line: string | null;
  reveal_mode: string; start_date: string | null; end_date: string | null; companions: string | null;
  order_status: string | null; photos: Moment[]; recipients: Recipient[]; }

export const createProject = (b: { title: string; start_date?: string; end_date?: string; companions?: string; cover_line?: string }) =>
  req<{ id: string }>("/api/v1/projects", { method: "POST", body: JSON.stringify(b) });
export const getProject = (id: string) => req<Project>(`/api/v1/projects/${id}`);
export const uploadPhotos = (id: string, files: File[]) => {
  const fd = new FormData(); files.forEach((f) => fd.append("files", f));
  return req<{ photos: Moment[] }>(`/api/v1/projects/${id}/photos`, { method: "POST", body: fd });
};
export const photoImageUrl = (momentId: string) => `${BASE}/api/v1/photos/${momentId}/image`;
export const uploadAudio = (momentId: string, blob: Blob) => {
  const fd = new FormData(); fd.append("file", blob, "voice.m4a");
  return req<{ id: string }>(`/api/v1/moments/${momentId}/audio`, { method: "POST", body: fd });
};
export const getAnalysis = (id: string) =>
  req<{ photos: { id: string; analysis_status: string; suggested_emotion: string | null; caption: string | null; transcript: string | null }[] }>(
    `/api/v1/projects/${id}/photos/analysis`);
export const patchMoment = (momentId: string, b: Partial<Pick<Moment, "emotion" | "note" | "caption">>) =>
  req(`/api/v1/moments/${momentId}`, { method: "PATCH", body: JSON.stringify(b) });
export const reorderMoments = (id: string, photo_ids: string[]) =>
  req(`/api/v1/projects/${id}/photos/order`, { method: "PATCH", body: JSON.stringify({ photo_ids }) });
export const addRecipient = (id: string, b: { name: string; address: string; phone?: string; gift_message?: string }) =>
  req<{ id: string }>(`/api/v1/projects/${id}/recipients`, { method: "POST", body: JSON.stringify(b) });
export const removeRecipient = (rid: string) => req(`/api/v1/recipients/${rid}`, { method: "DELETE" });
export const createOrder = (id: string, spec: object, shipping: object) =>
  req<{ book_uid: string; orders: { to: string; order_uid: string }[] }>(`/api/v1/projects/${id}/order`,
    { method: "POST", body: JSON.stringify({ spec, shipping }) });
export const getOrderStatus = (id: string) =>
  req<{ order_status: string | null; recipients: { name: string; order_status: string | null }[] }>(
    `/api/v1/projects/${id}/order/status`);
```

- [ ] **Step 3: library.ts** — `frontend/src/lib/library.ts`:
```typescript
/** 계정 없는 MVP의 "내 서재" — 이 기기에서 만든 여행 id 목록을 localStorage에 보관. */
const KEY = "tripbook.trips";
export const listTrips = (): string[] => { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } };
export const addTrip = (id: string) => { const t = listTrips().filter((x) => x !== id); localStorage.setItem(KEY, JSON.stringify([id, ...t])); };
export const removeTrip = (id: string) => localStorage.setItem(KEY, JSON.stringify(listTrips().filter((x) => x !== id)));
```

- [ ] **Step 4: index.css 디자인 토큰** — `frontend/src/index.css` 전체 교체. `design-v1.html`의 `<style>`에서 팔레트/버튼/카드/시트/파형/책 스타일을 컴포넌트 클래스로 옮긴다. 최소 포함: `:root` 토큰 변수, `.shell`(max-width 430 모바일 셸), `.book`(책등 그림자), `.card`/`.sheet`/`.wave`(카드+글귀+파형), `.book-page`/`.spread`(책 페이지/펼침면), `.btn`/`.btn-ghost`, `.chip`, `.emotion`, `.gift`, `.toggle`. 값은 Global Constraints의 토큰을 그대로 사용:
```css
:root{ --paper:#F7F4EE; --card:#fff; --ink:#191610; --soft:#8C8578; --line:#E7E1D6;
  --stamp:#E4531F; --stamp-soft:#FBE9E0; --serif:"Nanum Myeongjo",serif; --mono:"DM Mono",monospace;
  --sans:-apple-system,system-ui,"Malgun Gothic",sans-serif; }
*{box-sizing:border-box;margin:0}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased}
#root{min-height:100dvh;display:flex;justify-content:center}
.shell{width:100%;max-width:430px;min-height:100dvh}
/* 나머지 컴포넌트 클래스는 design-v1.html의 대응 규칙을 옮겨온다 (색은 위 변수 사용) */
```
> 구현자 노트: `design-v1.html`을 열어 각 화면(홈/덱/글귀시트/그리드/책/주문)의 CSS를 참고해 이 파일에 정리한다. 인라인 목업 스타일을 재사용 가능한 클래스로 만든다.

- [ ] **Step 5: index.html 폰트** — `frontend/index.html` `<head>`에 추가:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
```
그리고 `<title>Tripbook — 여행이 한 권의 책이 됩니다</title>`, `<html lang="ko">`.

- [ ] **Step 6: App.tsx 라우팅** — v1 위자드 라우트를 제거하고 v2 3화면으로. `frontend/src/App.tsx` 전체 교체:
```tsx
/** 라우터: 서재(/) · 새 여행(/new) · 앨범(/p/:id). 앨범 내부(덱/그리드/책/주문)는 그 컴포넌트의 상태로 전환. */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Library from "./screens/Library";
import NewTrip from "./screens/NewTrip";
import Album from "./screens/Album";

export default function App() {
  return (
    <BrowserRouter>
      <div className="shell">
        <Routes>
          <Route path="/" element={<Library />} />
          <Route path="/new" element={<NewTrip />} />
          <Route path="/p/:id" element={<Album />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
```
(스크린 컴포넌트는 다음 태스크. 이 태스크에선 각 파일에 `export default () => <p>준비 중</p>;` 임시 컴포넌트를 둬 빌드 통과: `frontend/src/screens/Library.tsx`, `NewTrip.tsx`, `Album.tsx`)

- [ ] **Step 7: 정리 + 확인** — v1 잔재 삭제: `rm -rf frontend/src/steps frontend/src/Wizard.tsx`. `frontend/src/utils.ts`의 `patchById`를 계속 쓰면 유지, 아니면 삭제. `npm test` PASS, `npm run build` 성공.

- [ ] **Step 8: 커밋** — `git add -A; git commit -m "feat(fe): v2 api client, design tokens, routing shell"`

---

### Task 2: 홈 — 여행 서재 (책장 진열)

**Files:**
- Modify: `frontend/src/screens/Library.tsx` (전체 교체)

**Interfaces:**
- Consumes: `listTrips`, `getProject`, `photoImageUrl`

- [ ] **Step 1: 구현** — `frontend/src/screens/Library.tsx` 전체 교체:
```tsx
/** 홈(서재): 이 기기에서 만든 여행을 책장에 책처럼 진열. 탭하면 그 여행이 열린다. */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listTrips, removeTrip } from "../lib/library";
import { getProject, photoImageUrl, type Project } from "../api";

export default function Library() {
  const nav = useNavigate();
  const [trips, setTrips] = useState<Project[]>([]);

  useEffect(() => {
    Promise.all(listTrips().map((id) => getProject(id).catch(() => null)))
      .then((ps) => {
        const ok = ps.filter((p): p is Project => !!p);
        // 삭제됐거나 못 찾는 여행 id는 서재에서 청소
        ok.forEach(() => {}); listTrips().filter((id) => !ok.some((p) => p.id === id)).forEach(removeTrip);
        setTrips(ok);
      });
  }, []);

  const cover = (p: Project) => p.photos[0] ? photoImageUrl(p.photos[0].id) : undefined;

  return (
    <div style={{ padding: "70px 20px 24px" }}>
      <h1 style={{ font: "800 27px/1.12 var(--sans)", letterSpacing: "-.03em" }}>여행 서재</h1>
      <p style={{ font: "400 12px/1.4 var(--mono)", color: "var(--soft)", margin: "8px 2px 26px" }}>
        {trips.length} TRIPS
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 13 }}>
        {trips.map((p) => (
          <button key={p.id} className="book" onClick={() => nav(`/p/${p.id}`)}
            style={cover(p) ? { backgroundImage: `url(${cover(p)})` } : { background: "#d9d2c5" }}>
            <span className="book-cap"><b>{p.title}</b><span>{p.photos.length} 순간</span></span>
          </button>
        ))}
        <button className="newbook" onClick={() => nav("/new")}><span>＋</span>새 여행</button>
      </div>
    </div>
  );
}
```
(`.book`, `.book-cap`, `.newbook` 스타일은 Task 1의 index.css에 `design-v1.html`의 홈 책장 규칙으로 정의되어 있어야 한다. 책 표지는 사진 배경 + 하단 그라디언트 캡션.)

- [ ] **Step 2: 확인** — `npm run build` 성공. 백엔드 켜고 프로젝트가 있으면 서재에 책으로 뜨는지, "새 여행" 이동 확인.

- [ ] **Step 3: 커밋** — `git commit -am "feat(fe): home library bookshelf"`

---

### Task 3: 새 여행 + 순간 담기 (사진 + 음성 녹음 + 감정)

**Files:**
- Modify: `frontend/src/screens/NewTrip.tsx` (전체 교체)
- Create: `frontend/src/components/Recorder.tsx` (MediaRecorder 훅/버튼)

**Interfaces:**
- Consumes: `createProject`, `addTrip`, `uploadPhotos`, `uploadAudio`, `patchMoment`, `getAnalysis`, `photoImageUrl`
- Produces: `Recorder` 컴포넌트 — `onRecorded(blob: Blob) => void`, 녹음/정지 토글 + 경과초 표시.

- [ ] **Step 1: Recorder 구현** — `frontend/src/components/Recorder.tsx`:
```tsx
/** 목소리 한 마디 녹음 버튼(MediaRecorder). 누르면 녹음, 다시 누르면 정지→onRecorded(blob). */
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
    m.onstop = () => { onRecorded(new Blob(chunks.current, { type: "audio/webm" })); stream.getTracks().forEach((t) => t.stop()); };
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
```

- [ ] **Step 2: NewTrip 구현** — `frontend/src/screens/NewTrip.tsx` 전체 교체:
```tsx
/** 새 여행 만들기 + 순간 담기: 제목 → 사진 추가 → 사진마다 목소리 녹음(자동 업로드→캡션) + 감정 탭. */
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, uploadPhotos, uploadAudio, patchMoment, photoImageUrl, type Moment } from "../api";
import { addTrip } from "../lib/library";
import Recorder from "../components/Recorder";

const EMOTIONS = ["설렘", "행복", "평온", "뭉클", "신남", "아쉬움"];

export default function NewTrip() {
  const nav = useNavigate();
  const [pid, setPid] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [companions, setCompanions] = useState("");
  const [moments, setMoments] = useState<Moment[]>([]);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const ensureProject = async (): Promise<string> => {
    if (pid) return pid;
    if (!title.trim()) { setError("여행 제목을 적어주세요"); throw new Error("no title"); }
    const { id } = await createProject({ title, companions: companions || undefined });
    addTrip(id); setPid(id); return id;
  };

  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    try {
      const id = await ensureProject();
      const { photos } = await uploadPhotos(id, [...files]);
      setMoments((cur) => [...cur, ...photos]);
    } catch (e) { if (e instanceof Error && e.message !== "no title") setError(e.message); }
  };

  const onAudio = async (m: Moment, blob: Blob) => {
    await uploadAudio(m.id, blob);
    // 캡션 생성 폴링(이 순간만): analysis_status done/failed까지
    const poll = setInterval(async () => {
      const p = await import("../api").then((a) => a.getAnalysis(pid!));
      const s = p.photos.find((x) => x.id === m.id);
      if (s && (s.analysis_status === "done" || s.analysis_status === "failed")) {
        clearInterval(poll);
        setMoments((cur) => cur.map((x) => (x.id === m.id ? { ...x, caption: s.caption, analysis_status: s.analysis_status } : x)));
      }
    }, 2000);
  };

  const setEmotion = (m: Moment, e: string) => { patchMoment(m.id, { emotion: e }); setMoments((cur) => cur.map((x) => x.id === m.id ? { ...x, emotion: e } : x)); };

  return (
    <div style={{ padding: "24px 20px 100px" }}>
      <input placeholder="여행 제목 — 예: 제주, 봄" value={title} onChange={(e) => setTitle(e.target.value)}
        style={{ font: "800 22px/1.3 var(--sans)", border: 0, background: "transparent", width: "100%", outline: "none" }} />
      <input placeholder="함께한 사람 (선택)" value={companions} onChange={(e) => setCompanions(e.target.value)}
        style={{ border: 0, borderBottom: "1px solid var(--line)", background: "transparent", width: "100%", padding: "8px 0", marginTop: 8 }} />

      <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e) => onFiles(e.target.files)} />
      <button className="btn-ghost" style={{ margin: "18px 0" }} onClick={() => fileRef.current?.click()}>＋ 사진 담기</button>

      {moments.map((m) => (
        <div key={m.id} className="capture-card">
          <img className="capture-thumb" src={photoImageUrl(m.id)} alt="" />
          <div style={{ flex: 1 }}>
            <Recorder onRecorded={(b) => onAudio(m, b)} />
            {m.analysis_status === "done" && m.caption && <p className="capture-cap">“{m.caption}”</p>}
            {m.analysis_status === "pending" && m.caption == null && <p className="capture-cap muted">녹음하면 여기에 글귀가 생겨요</p>}
            <div className="emotions">
              {EMOTIONS.map((e) => (
                <button key={e} className={"emotion" + (m.emotion === e ? " on" : "")} onClick={() => setEmotion(m, e)}>{e}</button>
              ))}
            </div>
          </div>
        </div>
      ))}

      {error && <p className="error-text">{error}</p>}
      {moments.length > 0 && (
        <div className="bottom-bar">
          <button className="btn" style={{ width: "100%" }} onClick={() => nav(`/p/${pid}`)}>여행 앨범 열기</button>
        </div>
      )}
    </div>
  );
}
```
(`.capture-card`, `.capture-thumb`, `.capture-cap`, `.rec` 스타일은 index.css에 추가.)

- [ ] **Step 2: 확인** — `npm run build` 성공. 브라우저에서 마이크 권한 허용 후 녹음→정지→(실키 있으면)캡션 생성, 감정 탭 동작. (실 OPENAI/ANTHROPIC 키 없으면 캡션은 failed 경로 — 크래시 없어야 함.)

- [ ] **Step 3: 커밋** — `git commit -am "feat(fe): new trip capture with voice recording + emotion"`

---

### Task 4: 앨범 — 카드 덱(스와이프) + 글귀 시트 + 전체 그리드

**Files:**
- Modify: `frontend/src/screens/Album.tsx` (전체 교체)
- Create: `frontend/src/components/MomentCard.tsx`, `frontend/src/components/Waveform.tsx`

**Interfaces:**
- Consumes: `getProject`, `photoImageUrl`, `type Project/Moment`
- Produces: `Album`은 내부 state `view: "deck" | "grid" | "book" | "order"`로 화면 전환. 이 태스크는 `deck`/`grid`만; `book`/`order`는 Task 5.

- [ ] **Step 1: Waveform** — `frontend/src/components/Waveform.tsx`:
```tsx
/** 시그니처: 앰버 음성 파형. 실제 오디오 분석 없이 결정적 막대 패턴(순간 id 시드)으로 그린다. */
export default function Waveform({ seed = 0, playing = false }: { seed?: number; playing?: boolean }) {
  const bars = Array.from({ length: 16 }, (_, i) => 5 + Math.round(15 * Math.abs(Math.sin((i + seed) * 1.3))));
  return (
    <span className="wave" aria-hidden>
      {bars.map((h, i) => <i key={i} style={{ height: h, animationDelay: `${i * 0.06}s` }} className={playing ? "on" : ""} />)}
    </span>
  );
}
```

- [ ] **Step 2: MomentCard** — `frontend/src/components/MomentCard.tsx`:
```tsx
/** 순간 카드: 풀블리드 사진 + 탭하면 글귀 시트(A 하단 슬라이드업) + 감정 칩 + 음성 파형 + 필름 날짜 스탬프. */
import { useState } from "react";
import { photoImageUrl, type Moment } from "../api";
import Waveform from "./Waveform";

export default function MomentCard({ m, index, stamp }: { m: Moment; index: number; stamp: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={"card" + (open ? " open" : "")} style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}
      onClick={() => setOpen((o) => !o)}>
      {m.emotion && <span className="chip">{m.emotion}</span>}
      {!open && <div className="taphint">탭하면 그때 내 말이 떠올라요</div>}
      <div className="sheet">
        <p className="q">{m.caption ?? m.transcript ?? "아직 목소리가 없는 순간"}</p>
        <div className="voice"><Waveform seed={index} playing={open} /><span className="lab">내 목소리</span><span className="st">{stamp}</span></div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Album (덱+그리드)** — `frontend/src/screens/Album.tsx` 전체 교체:
```tsx
/** 앨범: 카드 덱(스와이프) ⇄ ▦ 전체 그리드. 덱 끝엔 "책으로 만들기" 카드(Task 5). */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject, photoImageUrl, type Project } from "../api";
import MomentCard from "../components/MomentCard";

export default function Album() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState<Project | null>(null);
  const [idx, setIdx] = useState(0);
  const [view, setView] = useState<"deck" | "grid" | "book" | "order">("deck");

  useEffect(() => { getProject(id).then(setP); }, [id]);
  if (!p) return <div style={{ padding: 80, textAlign: "center", color: "var(--soft)" }}>여는 중…</div>;

  const M = p.photos;
  const stamp = (i: number) => `${(p.title || "TRIP").toUpperCase().slice(0, 6)} · ${String(i + 1).padStart(2, "0")}`;
  const atEnd = idx >= M.length;

  if (view === "grid") return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => setView("deck")}>‹ {p.title}</span><span className="ic on" onClick={() => setView("deck")}>▦</span></div>
      <div className="gwrap">
        {M.map((m, i) => (
          <button key={m.id} className="cell" style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}
            onClick={() => { setIdx(i); setView("deck"); }} />
        ))}
      </div>
    </div>
  );

  // book/order 뷰는 Task 5에서 렌더. 여기선 자리만.
  if (view === "book" || view === "order") return <div data-view={view} />;

  return (
    <div className="album-screen dark">
      <div className="bar light">
        <span onClick={() => nav("/")}>‹ {p.title}</span>
        <span className="ic" onClick={() => setView("grid")}>▦</span>
      </div>
      {!atEnd && <span className="counter">{String(idx + 1).padStart(2, "0")} / {String(M.length).padStart(2, "0")}</span>}
      <div className="deck">
        {atEnd ? (
          <div className="endcard">
            <div className="kick">{(p.title || "").toUpperCase()}</div>
            <h3>{M.length}개의 순간</h3>
            <p>여기까지가 이 여행이에요. 이대로 한 권의 책이 되면, 언제든 다시 펼쳐볼 수 있어요.</p>
            <button className="btn" onClick={() => setView("book")}>책으로 만들기</button>
            <button className="btn-ghost" onClick={() => setIdx(M.length - 1)}>← 순간 더 보기</button>
          </div>
        ) : (
          <MomentCard key={M[idx].id} m={M[idx]} index={idx} stamp={stamp(idx)} />
        )}
      </div>
      {!atEnd && (
        <>
          <span className="nav prev" onClick={() => setIdx((i) => Math.max(0, i - 1))}>‹</span>
          <span className="nav next" onClick={() => setIdx((i) => Math.min(M.length, i + 1))}>›</span>
          <div className="dots">{M.map((_, i) => <i key={i} className={i === idx ? "on" : ""} />)}</div>
        </>
      )}
    </div>
  );
}
```
(스와이프: 최소 버전은 ‹ › 버튼 + 도트. 터치 스와이프는 여유되면 pointer 핸들러 추가. `.album-screen`, `.bar`, `.deck`, `.endcard`, `.gwrap`, `.cell`, `.nav`, `.dots`, `.counter` 스타일은 index.css에 design-v1.html 기준으로 정의.)

- [ ] **Step 4: 확인** — `npm run build` 성공. 앨범 열기→카드 탭 시 글귀+파형, ‹ ›로 이동, ▦로 그리드, 끝 카드에서 "책으로 만들기"가 보이는지.

- [ ] **Step 5: 커밋** — `git commit -am "feat(fe): album card deck, moment reveal with waveform, grid toggle"`

---

### Task 5: 책 미리보기(펼침면) + 주문 + 선물

**Files:**
- Modify: `frontend/src/screens/Album.tsx` (book/order 뷰 구현)
- Create: `frontend/src/components/BookPreview.tsx`, `frontend/src/components/OrderSheet.tsx`

**Interfaces:**
- Consumes: `addRecipient`, `removeRecipient`, `createOrder`, `getOrderStatus`, `type Project/Moment`
- Produces: `BookPreview({project})` — 순간마다 펼침면(사진|캡션). `OrderSheet({project, onDone})` — 배송 입력 + 동행자 선물 토글 + 주문.

- [ ] **Step 1: BookPreview** — `frontend/src/components/BookPreview.tsx`:
```tsx
/** 책 펼침면 미리보기: 순간마다 왼쪽 사진 / 오른쪽 명조 캡션 + 필름 스탬프. "이대로 인쇄된다". */
import { photoImageUrl, type Project } from "../api";

export default function BookPreview({ project, onOrder }: { project: Project; onOrder: () => void }) {
  return (
    <div className="bookview">
      {project.photos.map((m, i) => (
        <div key={m.id} className="spread">
          <div className="pg photo" style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }} />
          <div className="spine" />
          <div className="pg txt"><div className="q">{m.caption ?? ""}</div><div className="st">NO.{String(i + 1).padStart(2, "0")}</div></div>
        </div>
      ))}
      <div className="bottom-bar">
        <button className="btn" style={{ width: "100%" }} onClick={onOrder}>이대로 만들기</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: OrderSheet** — `frontend/src/components/OrderSheet.tsx`:
```tsx
/** 주문 + 선물: 내 배송 입력 + (동행자에게) 선물 한 권 추가 → Sweetbook 주문. 완료 시 주문번호/상태. */
import { useState } from "react";
import { addRecipient, createOrder, type Project } from "../api";

const PRICE = 24000;
const BOOK_SPEC = { bookSpecUid: "REPLACE_ME", coverTemplateUid: "REPLACE_ME", contentTemplateUid: "REPLACE_ME" };

export default function OrderSheet({ project }: { project: Project }) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [gift, setGift] = useState(false);
  const [giftName, setGiftName] = useState(project.companions ?? "");
  const [giftAddr, setGiftAddr] = useState("");
  const [done, setDone] = useState<{ orders: { to: string; order_uid: string }[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const total = PRICE * (gift ? 2 : 1);

  const submit = async () => {
    if (!name || !address) return setError("받는 분과 주소를 적어주세요");
    setError(""); setBusy(true);
    try {
      if (gift && giftName && giftAddr) await addRecipient(project.id, { name: giftName, address: giftAddr });
      const res = await createOrder(project.id, BOOK_SPEC, { name, address });
      setDone(res);
    } catch (e) { setError(e instanceof Error ? e.message : "주문에 실패했어요"); } finally { setBusy(false); }
  };

  if (done) return (
    <div style={{ padding: "70px 22px" }}>
      <h2 style={{ font: "800 22px/1.3 var(--sans)" }}>책이 인쇄소로 떠났어요</h2>
      <div className="book-page" style={{ marginTop: 16 }}>
        {done.orders.map((o) => <p key={o.order_uid} style={{ margin: "6px 0" }}>{o.to} · <b>{o.order_uid}</b></p>)}
        <p className="muted" style={{ marginTop: 12, fontSize: 13 }}>인쇄와 제본이 끝나면 배송이 시작됩니다.</p>
      </div>
    </div>
  );

  return (
    <div style={{ padding: "70px 22px 24px" }}>
      <h2 style={{ font: "800 22px/1.3 var(--sans)" }}>한 권으로 만들어요</h2>
      <p className="muted" style={{ margin: "6px 0 20px", fontSize: 13 }}>{project.photos.length}개의 순간이 손에 쥐는 한 권이 됩니다.</p>
      <label>받는 분</label><input value={name} onChange={(e) => setName(e.target.value)} />
      <label>주소</label><input value={address} onChange={(e) => setAddress(e.target.value)} />

      <div className="gift">
        <div className="g-top"><div className="g-face" /><div><b>{project.companions || "함께한 사람"}에게도 한 권</b><span>같은 책을 선물로 보내기</span></div></div>
        <div className="g-row"><span className="lab">선물 추가 · {PRICE.toLocaleString()}원</span>
          <div className={"toggle" + (gift ? " on" : "")} onClick={() => setGift((g) => !g)}><b /></div></div>
        {gift && (<div style={{ marginTop: 10 }}>
          <input placeholder="받는 분 이름" value={giftName} onChange={(e) => setGiftName(e.target.value)} />
          <input placeholder="선물 배송 주소" value={giftAddr} onChange={(e) => setGiftAddr(e.target.value)} style={{ marginTop: 8 }} />
        </div>)}
      </div>

      <div className="total"><span>합계</span><b>{total.toLocaleString()}원</b></div>
      {error && <p className="error-text">{error}</p>}
      <button className="btn" style={{ width: "100%" }} disabled={busy} onClick={submit}>{busy ? "책을 만드는 중…" : "주문하기"}</button>
      <p style={{ font: "400 11px/1.6 var(--mono)", color: "var(--soft)", textAlign: "center", marginTop: 12 }}>SWEETBOOK 인쇄·배송</p>
    </div>
  );
}
```

- [ ] **Step 3: Album에 book/order 연결** — `Album.tsx`의 `if (view === "book" || view === "order")` 자리를 실제 렌더로 교체:
```tsx
  if (view === "book") return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => setView("deck")}>‹ 미리보기</span></div>
      <BookPreview project={p} onOrder={() => setView("order")} />
    </div>
  );
  if (view === "order") return (
    <div className="album-screen light">
      <div className="bar dark"><span onClick={() => setView("book")}>‹ 주문</span></div>
      <OrderSheet project={p} />
    </div>
  );
```
(상단 import에 `BookPreview`, `OrderSheet` 추가.)

- [ ] **Step 4: 확인** — `npm run build` 성공. 끝 카드→책 미리보기(펼침면)→주문, 선물 토글 시 합계 2배, (모킹/실키로) 주문 완료 화면.

- [ ] **Step 5: 커밋** — `git commit -am "feat(fe): book preview spreads + order with gifting"`

---

### Task 6: 마무리 — 빌드·문서·데모 확인

**Files:**
- Modify: `docs/CODE_TOUR.md`(프론트 v2 섹션 교체), `README.md`(스크린샷/실행), `frontend/src/index.css`(누락 스타일 보강)

- [ ] **Step 1: CODE_TOUR 프론트 섹션 교체** — v1 위자드 항목(Step1~5, Wizard)을 v2 화면으로: `api.ts` → `lib/library.ts` → `App.tsx` → `screens/{Library,NewTrip,Album}.tsx` → `components/{Recorder,MomentCard,Waveform,BookPreview,OrderSheet}.tsx`. 각 1줄 역할 + "여기서 볼 것".

- [ ] **Step 2: README v2 갱신** — 소개(음성 캡션 포토북), 화면 구조(서재→덱→글귀→책→주문), 실행 방법(backend/frontend/.env에 ANTHROPIC/OPENAI/SWEETBOOK), "Claude Code와 함께 만든 과정"(피벗·디자인 반복·SDD). `BOOK_SPEC`의 `REPLACE_ME`는 Sandbox 확정 시 교체 명시.

- [ ] **Step 3: 스타일 보강 + 전체 확인** — 앞 태스크에서 빠진 컴포넌트 클래스가 있으면 `design-v1.html` 기준으로 index.css에 채운다. `npm test` PASS, `npm run build` 성공.

- [ ] **Step 4: (수동) 스크린샷 확인** — 백엔드(uvicorn) + 프론트(npm run dev) 실행, 서재→새 여행(사진2장+녹음)→앨범 덱→글귀→책→주문(모킹) 통주. 폰 뷰에서 필름/명조/앰버 파형이 목업(design-v1)과 일치하는지.

- [ ] **Step 5: 커밋** — `git commit -am "docs(fe): v2 code tour + readme, style polish"`

---

## Self-Review 결과

- **스펙 커버리지:** api v2 클라이언트(§API, T1), 서재 책장(§3.5 홈, T2), 순간 담기+음성 녹음(§3 플로우·§6 Whisper, T3), 카드 덱+글귀 시트+음성 파형+그리드(§3.5·3.6 시그니처, T4), 책 펼침면+주문+선물(§2 수익·§3, T5), 문서(T6). 백엔드는 Plan A에서 완료.
- **디자인 충실도:** 색·타이포·시그니처는 `design-v1.html`을 단일 기준으로 삼는다(각 컴포넌트 태스크가 참조). index.css는 그 목업의 인라인 스타일을 재사용 클래스로 옮긴 것.
- **음성/캡션 수명:** 캡션 폴링은 audio를 올린 순간에만 건다(백엔드 노트: audio 없는 순간은 analysis_status가 pending 고착 — 무한 로딩 금지). done/failed 양쪽에서 폴링 종료.
- **타입 일관성:** `Moment`(caption/transcript/emotion/analysis_status), `createOrder`가 `{orders:[{to,order_uid}]}` 반환, `addRecipient` 등 함수명이 백엔드 v2 계약과 일치.
- **미확정:** `BOOK_SPEC`의 `REPLACE_ME` 3개는 Sweetbook Sandbox/포털 값으로 확정. MediaRecorder mimeType은 브라우저별 상이(webm/m4a) — 백엔드는 확장자와 무관하게 Whisper에 그대로 전달하므로 무해.
