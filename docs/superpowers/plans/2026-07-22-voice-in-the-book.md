# "목소리가 책에 산다" (Voice in the Book) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 순간마다 내 실제 녹음을 앱에서 재생(진짜 파형)하고, 실물 책엔 QR을 인쇄해 스캔하면 공개 페이지 `/v/:id`에서 그때 목소리를 다시 듣게 한다.

**Architecture:** 백엔드는 오디오 파일을 서빙하고 공개 순간 조회를 제공한다. 렌더러는 인쇄 이미지 하단에 종이색 밴드를 덧대 그 안에 QR을 합성한다. 프론트는 Web Audio로 오디오를 디코드해 진짜 파형+재생을 그리고, `/v/:id` 공개 페이지가 QR 목적지가 된다.

**Tech Stack:** FastAPI, SQLAlchemy, Pillow, `qrcode`(신규), OpenAI Whisper(`whisper-1`), React 19 + TS + Vite, Web Audio API, react-router-dom.

**Spec:** `docs/superpowers/specs/2026-07-22-voice-in-the-book-design.md`

## Global Constraints

- 음성 전사는 **`whisper-1`** 고정(CLAUDE.md). `budget_tokens`/`temperature` 금지. API 키는 `.env`로만.
- 디자인 토큰(§3.6): 종이 `#F7F4EE`, 먹 `#191610`, 타우프 `#8C8578`, 라인 `#E7E1D6`, 앰버 `#E4531F`(악센트만). 글귀=명조 `Nanum Myeongjo`, 카운터/스탬프=`DM Mono`.
- 캡션 불변식 `NO_INVENTION`(창작 금지) 유지 — 이 플랜은 캡션 로직을 바꾸지 않는다.
- 새 파일 만들면 `docs/CODE_TOUR.md`에 1줄 추가. 커밋은 태스크마다 최소 1회, conventional commits.
- QR 위치 = **사진 위 아님, 하단 종이색 밴드**(2-b 결정). 사진 원본 픽셀 불변.
- 검증: 백엔드 `cd backend; python -m pytest tests/ -v`, 프론트 `cd frontend; npm test && npm run build`.
- 오디오 없는 순간은 무한로딩/에러 금지 — 플레이어 숨기고 QR 생략.

---

### Task 1: 설정 + STT 한국어 튜닝

**Files:**
- Modify: `backend/app/config.py`, `backend/app/ai/stt.py`
- Test: `backend/tests/test_stt.py` (create)

**Interfaces:**
- Produces: `Settings.public_web_base: str` (QR 목적지 베이스). `stt.transcribe(path)` 가 Whisper에 `language="ko"` 전달.

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_stt.py` 생성:
```python
def test_transcribe_passes_korean_language(monkeypatch, tmp_path):
    import app.ai.stt as stt
    calls = {}
    class Tx:
        @staticmethod
        def create(**kw):
            calls.update(kw)
            return type("R", (), {"text": "  안녕  "})()
    class FakeClient:
        class audio:  # noqa
            transcriptions = Tx
    monkeypatch.setattr(stt, "get_stt_client", lambda: FakeClient())
    f = tmp_path / "a.m4a"; f.write_bytes(b"x")
    out = stt.transcribe(str(f))
    assert out == "안녕"
    assert calls["language"] == "ko"
    assert calls["model"] == "whisper-1"
```

- [ ] **Step 2: 실패 확인** — Run: `cd backend; python -m pytest tests/test_stt.py -v` → FAIL(`language` KeyError).

- [ ] **Step 3: 구현** — `backend/app/ai/stt.py`의 `transcribe` 교체:
```python
def transcribe(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        res = get_stt_client().audio.transcriptions.create(
            model="whisper-1", file=f, language="ko",
            prompt="여행 중 남긴 짧은 한국어 음성 메모",
        )
    return res.text.strip()
```

- [ ] **Step 4: config에 public_web_base 추가** — `backend/app/config.py`의 `Settings`에 필드 추가(‎`database_url` 아래):
```python
    public_web_base: str = "http://localhost:5173"  # 인쇄 QR이 가리킬 공개 웹 주소
```

- [ ] **Step 5: 통과 확인** — Run: `cd backend; python -m pytest tests/test_stt.py -v` → PASS.

- [ ] **Step 6: 커밋** — `git add -A; git commit -m "feat(stt): Korean language hint + public_web_base setting"`

---

### Task 2: 오디오 서빙 엔드포인트

**Files:**
- Modify: `backend/app/routers/photos.py`
- Test: `backend/tests/test_audio.py` (create)

**Interfaces:**
- Produces: `GET /api/v1/moments/{photo_id}/audio` → 오디오 파일(FileResponse), content-type을 바이트로 스니핑. 오디오 없으면 404.

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_audio.py` 생성:
```python
def _seed_photo(client, monkeypatch):
    import app.ai.analysis as analysis, app.ai.caption as caption
    monkeypatch.setattr(analysis, "analyze_batch", lambda ids: None)
    monkeypatch.setattr(caption, "transcribe_and_caption", lambda pid: None)
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (10, 10)).save(buf, "JPEG")
    pid = client.post("/api/v1/projects", json={"title": "제주"}).json()["id"]
    m = client.post(f"/api/v1/projects/{pid}/photos",
                    files=[("files", ("a.jpg", buf.getvalue(), "image/jpeg"))]).json()["photos"][0]
    return m["id"]

def test_audio_404_when_no_audio(client, monkeypatch):
    mid = _seed_photo(client, monkeypatch)
    assert client.get(f"/api/v1/moments/{mid}/audio").status_code == 404

def test_audio_served_with_webm_content_type(client, monkeypatch):
    mid = _seed_photo(client, monkeypatch)
    webm = b"\x1a\x45\xdf\xa3" + b"\x00" * 40  # EBML(webm) 헤더
    client.post(f"/api/v1/moments/{mid}/audio", files=[("file", ("v.m4a", webm, "audio/webm"))])
    r = client.get(f"/api/v1/moments/{mid}/audio")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/webm")
```

- [ ] **Step 2: 실패 확인** — Run: `cd backend; python -m pytest tests/test_audio.py -v` → FAIL(404 라우트 없음/405).

- [ ] **Step 3: 구현** — `backend/app/routers/photos.py`:
  - 상단 import 줄을 교체(‎`os`·`HTTPException` 추가):
```python
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, HTTPException
```
  - 파일 하단(‎`patch_moment` 위)에 추가:
```python
def _audio_media_type(path: str) -> str:
    with open(path, "rb") as f:
        head = f.read(12)
    if head[:4] == b"\x1a\x45\xdf\xa3":   # EBML → webm/matroska
        return "audio/webm"
    if head[4:8] == b"ftyp":              # ISO-BMFF → m4a/mp4
        return "audio/mp4"
    return "application/octet-stream"


@router.get("/moments/{photo_id}/audio")
def moment_audio(photo_id: str, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    if not photo.audio_path or not os.path.exists(photo.audio_path):
        raise HTTPException(404, "no audio")
    return FileResponse(photo.audio_path, media_type=_audio_media_type(photo.audio_path))
```

- [ ] **Step 4: 통과 확인** — Run: `cd backend; python -m pytest tests/test_audio.py -v` → PASS.

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "feat(audio): serve moment audio with sniffed content-type"`

---

### Task 3: 공개 순간 조회 엔드포인트

**Files:**
- Modify: `backend/app/routers/photos.py`
- Test: `backend/tests/test_public_moment.py` (create)

**Interfaces:**
- Produces: `GET /api/v1/moments/{photo_id}` → `{id, caption, transcript, emotion, project_title, has_audio}`. 인증 없음. 없는 id → 404.

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_public_moment.py` 생성:
```python
from tests.test_audio import _seed_photo

def test_public_moment_shape(client, monkeypatch):
    mid = _seed_photo(client, monkeypatch)
    client.patch(f"/api/v1/moments/{mid}", json={"caption": "바다가 파랬다", "emotion": "평온"})
    r = client.get(f"/api/v1/moments/{mid}")
    assert r.status_code == 200
    b = r.json()
    assert b["caption"] == "바다가 파랬다"
    assert b["emotion"] == "평온"
    assert b["project_title"] == "제주"
    assert b["has_audio"] is False

def test_public_moment_404(client):
    assert client.get("/api/v1/moments/nope").status_code == 404
```

- [ ] **Step 2: 실패 확인** — Run: `cd backend; python -m pytest tests/test_public_moment.py -v` → FAIL.
  (주: `GET /moments/{id}` 는 `GET /moments/{id}/audio` 와 경로가 안 겹친다 — audio는 하위 세그먼트.)

- [ ] **Step 3: 구현** — `backend/app/routers/photos.py`:
  - 상단 import에 `Project` 추가: `from app.models import Photo, Project`
  - `_audio_media_type` 아래에 추가:
```python
@router.get("/moments/{photo_id}")
def get_moment(photo_id: str, db: Session = Depends(get_db)):
    photo = get_or_404(db, Photo, photo_id, "moment")
    project = db.get(Project, photo.project_id)
    return {
        "id": photo.id, "caption": photo.caption, "transcript": photo.transcript,
        "emotion": photo.emotion, "project_title": project.title if project else "",
        "has_audio": bool(photo.audio_path),
    }
```

- [ ] **Step 4: 통과 확인** — Run: `cd backend; python -m pytest tests/test_public_moment.py -v` → PASS. 이어서 전체: `python -m pytest tests/ -q` → 그린.

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "feat(moments): public moment view endpoint for /v/:id"`

---

### Task 4: 프론트 API 클라이언트 (audioUrl, getMoment)

**Files:**
- Modify: `frontend/src/api.ts`, `frontend/src/api.test.ts`

**Interfaces:**
- Produces: `audioUrl(id): string`, `getMoment(id): Promise<PublicMoment>`, 타입 `PublicMoment`.

- [ ] **Step 1: 실패 테스트** — `frontend/src/api.test.ts`의 `describe("api v2", …)` 안에 추가:
```typescript
  it("getMoment fetches /api/v1/moments/{id}", async () => {
    const { getMoment } = await import("./api");
    await getMoment("m9");
    const [url] = (fetch as any).mock.calls.at(-1);
    expect(url).toContain("/api/v1/moments/m9");
    expect(url).not.toContain("/audio");
  });
```

- [ ] **Step 2: 실패 확인** — Run: `cd frontend; npm test` → FAIL(`getMoment` 없음).

- [ ] **Step 3: 구현** — `frontend/src/api.ts` 하단에 추가:
```typescript
export interface PublicMoment { id: string; caption: string | null; transcript: string | null;
  emotion: string | null; project_title: string; has_audio: boolean; }
export const audioUrl = (momentId: string) => `${BASE}/api/v1/moments/${momentId}/audio`;
export const getMoment = (id: string) => req<PublicMoment>(`/api/v1/moments/${id}`);
```

- [ ] **Step 4: 통과 확인** — Run: `cd frontend; npm test` → PASS.

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "feat(fe): api audioUrl + getMoment (public moment)"`

---

### Task 5: 진짜 파형 컴포넌트 + MomentCard 연결

**Files:**
- Create: `frontend/src/components/AudioWaveform.tsx`
- Modify: `frontend/src/components/MomentCard.tsx`, `frontend/src/index.css`
- Delete: `frontend/src/components/Waveform.tsx` (대체)

**Interfaces:**
- Consumes: `audioUrl` (Task 4).
- Produces: `AudioWaveform({ src, bars? })` — 오디오를 Web Audio로 디코드해 실제 진폭 막대 + 탭 재생/진행. 오디오 없거나 디코드 실패 시 정적 막대(폴백).

- [ ] **Step 1: AudioWaveform 구현** — `frontend/src/components/AudioWaveform.tsx`:
```tsx
/** 시그니처: 진짜 음성 파형 + 재생. 오디오를 Web Audio로 디코드해 진폭 막대를 그리고, 탭하면 재생/진행 표시.
 *  누가 호출: MomentCard, screens/Voice.
 *  무엇을 호출: fetch(src) + AudioContext.decodeAudioData + <audio>. */
import { useEffect, useRef, useState } from "react";

export default function AudioWaveform({ src, bars = 32 }: { src: string; bars?: number }) {
  const [peaks, setPeaks] = useState<number[]>([]);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(src);
        if (!res.ok) return;
        const buf = await res.arrayBuffer();
        const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const ctx = new AC();
        const decoded = await ctx.decodeAudioData(buf);
        const data = decoded.getChannelData(0);
        const block = Math.floor(data.length / bars) || 1;
        const out: number[] = [];
        for (let i = 0; i < bars; i++) {
          let sum = 0;
          for (let j = 0; j < block; j++) sum += Math.abs(data[i * block + j] || 0);
          out.push(sum / block);
        }
        const max = Math.max(...out, 1e-4);
        if (!cancelled) setPeaks(out.map((v) => v / max));
        ctx.close();
      } catch { /* 폴백 정적 막대 사용 */ }
    })();
    return () => { cancelled = true; };
  }, [src, bars]);

  const shown = peaks.length ? peaks : Array.from({ length: bars }, (_, i) => 0.35 + 0.4 * Math.abs(Math.sin(i)));
  const active = Math.floor(progress * shown.length);
  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    const a = audioRef.current; if (!a) return;
    if (playing) a.pause(); else void a.play();
  };

  return (
    <span className="wave" onClick={toggle} role="button" aria-label={playing ? "일시정지" : "재생"}>
      {shown.map((h, i) => (
        <i key={i} style={{ height: 5 + Math.round(17 * h) }} className={playing && i <= active ? "on" : ""} />
      ))}
      <audio ref={audioRef} src={src} preload="none"
        onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
        onEnded={() => { setPlaying(false); setProgress(0); }}
        onTimeUpdate={(e) => { const a = e.currentTarget; setProgress(a.duration ? a.currentTime / a.duration : 0); }} />
    </span>
  );
}
```

- [ ] **Step 2: MomentCard 연결** — `frontend/src/components/MomentCard.tsx`에서 `Waveform` import를 `AudioWaveform`으로 교체하고, `audioUrl`을 import. `<Waveform seed={index} playing={open} />` 를 아래로 교체:
```tsx
import AudioWaveform from "./AudioWaveform";
import { photoImageUrl, audioUrl, type Moment } from "../api";
```
그리고 voice 줄:
```tsx
        <div className="voice"><AudioWaveform src={audioUrl(m.id)} /><span className="lab">내 목소리</span><span className="st">{stamp}</span></div>
```
(‎`Waveform` import 제거. `index` prop은 더 이상 파형에 안 쓰지만 `stamp` 계산엔 무관 — 시그니처 유지.)

- [ ] **Step 3: index.css 파형 재생 상태** — `frontend/src/index.css`의 `.wave i` 규칙을 교체(진행 채움):
```css
.wave i{ width:2.5px; border-radius:2px; background:var(--stamp); opacity:.5; }
.wave i.on{ opacity:1; }
```
(기존 `.wave i.on{ animation:wavepulse … }` 및 `@keyframes wavepulse`는 제거 — 이제 진행 표시로 대체.)

- [ ] **Step 4: 잔재 삭제 + 빌드** — `rm frontend/src/components/Waveform.tsx`. Run: `cd frontend; npm run build` → 성공(타입체크 포함).

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "feat(fe): real audio waveform + playback, replace fake Waveform"`

---

### Task 6: 공개 재생 페이지 /v/:id

**Files:**
- Create: `frontend/src/screens/Voice.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/index.css`

**Interfaces:**
- Consumes: `getMoment`, `photoImageUrl`, `audioUrl` (Task 4), `AudioWaveform` (Task 5).

- [ ] **Step 1: Voice 페이지** — `frontend/src/screens/Voice.tsx`:
```tsx
/** 공개 재생 페이지(인쇄 QR 목적지): 사진 + 명조 글귀 + 진짜 파형으로 그때 목소리를 다시 듣는다.
 *  누가 호출: App 라우터(/v/:id).
 *  무엇을 호출: api(getMoment/photoImageUrl/audioUrl), components/AudioWaveform. */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getMoment, photoImageUrl, audioUrl, type PublicMoment } from "../api";
import AudioWaveform from "../components/AudioWaveform";

export default function Voice() {
  const { id = "" } = useParams();
  const [m, setM] = useState<PublicMoment | "loading" | "missing">("loading");
  useEffect(() => { getMoment(id).then(setM).catch(() => setM("missing")); }, [id]);
  if (m === "loading") return <div className="voice-empty">여는 중…</div>;
  if (m === "missing") return <div className="voice-empty">이 순간은 더 이상 없어요.</div>;
  return (
    <div className="voice-page" style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}>
      <div className="voice-sheet">
        {m.emotion && <span className="chip">{m.emotion}</span>}
        <p className="q">{m.caption ?? m.transcript ?? "그때의 목소리"}</p>
        {m.has_audio && (
          <div className="voice">
            <AudioWaveform src={audioUrl(m.id)} /><span className="lab">그때 목소리</span><span className="st">{m.project_title}</span>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 라우트 추가** — `frontend/src/App.tsx`에 import와 Route 추가:
```tsx
import Voice from "./screens/Voice";
```
`<Route path="/p/:id" element={<Album />} />` 아래에:
```tsx
          <Route path="/v/:id" element={<Voice />} />
```

- [ ] **Step 3: index.css 공개 페이지 스타일** — `frontend/src/index.css` 하단(`:focus-visible` 위)에 추가:
```css
/* 공개 재생 페이지 /v/:id */
.voice-page{ position:relative; min-height:100dvh; background:#100c08 center/cover no-repeat; }
.voice-sheet{ position:absolute; left:0; right:0; bottom:0; padding:80px 24px 40px;
  background:linear-gradient(transparent,rgba(10,6,3,.5) 30%,rgba(10,6,3,.94) 74%); }
.voice-sheet .q{ color:#fff; font:400 21px/1.85 var(--serif); word-break:keep-all; white-space:pre-line; }
.voice-empty{ min-height:100dvh; display:flex; align-items:center; justify-content:center;
  color:var(--soft); font:400 15px/1.6 var(--sans); text-align:center; padding:24px; }
```

- [ ] **Step 4: 빌드** — Run: `cd frontend; npm run build` → 성공.

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "feat(fe): public /v/:id voice playback page (QR destination)"`

---

### Task 7: 인쇄 QR 밴드 합성 (렌더러)

**Files:**
- Modify: `backend/requirements.txt`, `backend/app/sweetbook/renderer.py`
- Test: `backend/tests/test_qr.py` (create)

**Interfaces:**
- Consumes: `Settings.public_web_base` (Task 1).
- Produces: `renderer.compose_page_image(photo_bytes: bytes, url: str) -> bytes` — 사진 아래 종이색 밴드 + QR을 합성한 JPEG 바이트. 렌더러는 audio 있는 순간에만 이걸 태운다.

- [ ] **Step 1: qrcode 의존성 추가 + 설치** — `backend/requirements.txt`에 한 줄 추가:
```
qrcode>=7.4
```
Run: `cd backend; pip install "qrcode>=7.4"`

- [ ] **Step 2: 실패 테스트** — `backend/tests/test_qr.py` 생성:
```python
import io
from PIL import Image


def _jpeg(color, size=(300, 300)):
    b = io.BytesIO(); Image.new("RGB", size, color).save(b, "JPEG"); return b.getvalue()


def test_compose_adds_band_and_qr():
    from app.sweetbook.renderer import compose_page_image
    out = compose_page_image(_jpeg((12, 12, 12)), "http://x/v/abc")
    img = Image.open(io.BytesIO(out))
    assert img.height > 300  # 하단 밴드가 추가됨
    band = img.crop((0, 300, img.width, img.height))
    colors = {c for _, c in (band.getcolors(maxcolors=200000) or [])}
    assert (255, 255, 255) in colors  # QR 흰 모듈 존재
    assert (247, 244, 238) in colors  # 종이색 밴드
```

- [ ] **Step 3: 실패 확인** — Run: `cd backend; python -m pytest tests/test_qr.py -v` → FAIL(`compose_page_image` 없음).

- [ ] **Step 4: 구현** — `backend/app/sweetbook/renderer.py`:
  - 상단 import 추가:
```python
import io
import qrcode
from PIL import Image
from app.config import get_settings
```
  - `_image` 아래에 추가:
```python
def compose_page_image(photo_bytes: bytes, url: str, band_ratio: float = 0.18) -> bytes:
    """사진 아래에 종이색 밴드를 덧대고 그 안에 QR을 합성. 사진 원본 픽셀은 건드리지 않는다(2-b)."""
    base = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    w, h = base.size
    band = int(h * band_ratio)
    canvas = Image.new("RGB", (w, h + band), (247, 244, 238))  # 종이색 #F7F4EE
    canvas.paste(base, (0, 0))
    qr = qrcode.make(url).convert("RGB")               # 흰 quiet-zone 포함
    qs = int(band * 0.82)
    qr = qr.resize((qs, qs))
    canvas.paste(qr, (w - qs - int(band * 0.12), h + (band - qs) // 2))
    out = io.BytesIO(); canvas.save(out, "JPEG", quality=90)
    return out.getvalue()
```
  - `render`의 순간 루프에서 사진 바이트 준비 부분을 교체 — 기존:
```python
        for m in moments:
            r = self.client.add_content(
                book_uid, content_uid,
                {"caption": getattr(m, "caption", None) or "", "photo": "$upload"},
                {"photo": ("p.jpg", _image(m.file_path), "image/jpeg")}, break_before="page")
```
  로 교체:
```python
        web_base = get_settings().public_web_base
        for m in moments:
            img = _image(m.file_path)
            if getattr(m, "audio_path", None):  # 오디오 있는 순간만 QR 밴드
                img = compose_page_image(img, f"{web_base}/v/{getattr(m, 'id', '')}")
            r = self.client.add_content(
                book_uid, content_uid,
                {"caption": getattr(m, "caption", None) or "", "photo": "$upload"},
                {"photo": ("p.jpg", img, "image/jpeg")}, break_before="page")
```
  (패딩 루프의 `_image(moments[-1].file_path)` 는 그대로 — 여백 페이지엔 QR 불필요.)

- [ ] **Step 5: 통과 확인** — Run: `cd backend; python -m pytest tests/test_qr.py tests/test_sweetbook.py tests/test_orders.py -v` → 모두 PASS. (기존 렌더러 테스트의 스텁 순간은 `audio_path`가 없어 QR 경로를 안 탄다.)

- [ ] **Step 6: 커밋** — `git add -A; git commit -m "feat(print): composite QR band under photo, links to /v/:id"`

---

### Task 8: 마무리 — 문서 + 실 Sandbox QR 렌더 확인

**Files:**
- Modify: `docs/CODE_TOUR.md`, `backend/.env.example`

- [ ] **Step 1: .env.example에 공개 주소** — `backend/.env.example`(없으면 리포 루트 `.env.example`)에 한 줄 추가:
```
PUBLIC_WEB_BASE=http://localhost:5173
```

- [ ] **Step 2: CODE_TOUR 갱신** — `docs/CODE_TOUR.md`에 신규 파일 1줄씩 추가: `AudioWaveform.tsx`(진짜 파형+재생), `screens/Voice.tsx`(공개 재생 페이지 /v/:id), photos 라우터의 `moment_audio`·`get_moment`, renderer의 `compose_page_image`(인쇄 QR 밴드). MomentCard 항목의 "파형" 설명을 "실제 오디오 파형+재생"으로 수정.

- [ ] **Step 3: 전체 테스트 + 빌드** — Run: `cd backend; python -m pytest tests/ -q` → 그린. Run: `cd frontend; npm test && npm run build` → 그린.

- [ ] **Step 4: (실 Sandbox) QR 인쇄 확인** — `.env`에 SWEETBOOK 키 있는 상태에서, 오디오 있는 순간 1개로 책을 렌더해 QR 밴드가 내지에 어떻게 앉는지 확인한다(오픈 아이템). 아래 스니펫을 `cd backend; python -` 로 실행:
```python
import io, os, sys, tempfile
sys.path.insert(0, ".")
from PIL import Image
from app.config import get_settings
from app.sweetbook.client import SweetbookClient
from app.sweetbook.renderer import TemplateRenderer
s = get_settings(); c = SweetbookClient(s.sweetbook_api_key, s.sweetbook_env)
SPEC = {"bookSpecUid": "SQUAREBOOK_HC", "coverTemplateUid": "79yjMH3qRPly", "contentTemplateUid": "2mi1ao0Z4Vxl"}
tmp = tempfile.mkdtemp()
p = os.path.join(tmp, "m.jpg"); Image.new("RGB", (1200, 1200), (90, 140, 180)).save(p, "JPEG")
class M:  # 오디오 있는 순간(QR 밴드 경로 강제)
    id = "demo-moment"; file_path = p; caption = "바다가 파랬다"; audio_path = "x"
class P:
    title = "제주, 봄"; cover_line = "우리의 첫 봄"; start_date = "2025.04.12"; end_date = "2025.04.14"
print("book:", TemplateRenderer(c).render(P(), [M()], SPEC))
```
QR이 너무 작아 스캔이 안 되면 `compose_page_image`의 `band_ratio`(0.18)를 키워 재확인. 템플릿에 QR 전용 슬롯이 있으면 그쪽으로 전환 고려(스펙 오픈 아이템).

- [ ] **Step 5: 커밋** — `git add -A; git commit -m "docs: code tour + env for voice-in-the-book; verify printed QR"`

---

## Self-Review 결과

- **스펙 커버리지:** 오디오 서빙(T2), 공개 순간 조회(T3), 공개 재생 페이지 /v/:id(T6), 진짜 파형(T5), 인쇄 QR 밴드(T7, 2-b), STT 한국어 튜닝(T1), public_web_base 설정(T1/T8). 데이터 모델 변경 없음(스펙 §4)과 일치.
- **타입 일관성:** `audioUrl`/`getMoment`/`PublicMoment`(T4)를 Voice/MomentCard가 그대로 소비. `compose_page_image(bytes,url)->bytes`(T7) 시그니처가 렌더러 호출과 일치. `get_moment` 응답 키(caption/emotion/project_title/has_audio)가 프론트 `PublicMoment`와 일치.
- **플레이스홀더:** 없음 — 모든 코드 스텝에 실제 코드/명령/기대결과 포함.
- **오픈 아이템(구현 중):** 인쇄 QR 스캔 크기(T8 Step4에서 실 렌더로 눈 확인, band_ratio 조정), 오디오 mime는 스니핑으로 처리(T2). ANTHROPIC 키는 캡션 실작동용 env 작업(플랜 외).
- **의존성:** `qrcode` 신규(T7 Step1). Pillow/openai/anthropic 기존.
