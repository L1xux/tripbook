# Tripbook 시그니처 — "목소리가 책에 산다" (Voice lives in the book) 설계

> THE 한방(①). 근거·경쟁분석·셀링포인트: `2026-07-22-voice-in-the-book-competitive-and-selling-points.md`.
> 스코프는 **① 단독(목소리)**. ②감정 리마인드·⑤in-trip 캡처는 이 스펙 밖(다음 단계).

## 1. 목표

앱에서 순간 카드를 탭하면 **내 실제 녹음이 재생**되고 **진짜 음성 파형**이 그려진다.
실물 책에는 순간마다 **QR**이 인쇄되어, 스캔하면 **공개 재생 페이지(`/v/:id`)** 에서 그때의 목소리를 다시 듣는다.
= "종이책을 펼치면 그때 내 목소리가 흘러나온다." (Remento 벤치마크, 여행 세그먼트로.)

**해결하는 문제:** 지금 파형은 가짜(`Math.sin`), 녹음 재생 기능 없음, AI가 안 느껴짐 → 제품 정체성(§3.6 "앰버 음성 파형=진짜 목소리")이 미구현.

## 2. 스코프

**포함:** ① 오디오 서빙 · ② 공개 순간 조회 · ③ 공개 재생 페이지 `/v/:id` · ④ 진짜 파형 컴포넌트(앱+공개) ·
⑤ 인쇄 QR 합성 · ⑥ STT 한국어 튜닝 · ⑦ 공개 웹 주소 설정.
**제외(YAGNI, 다음 단계):** 감정 리마인드(②), in-trip 캡처(⑤), 목소리 prosody 감정분석(④), 협업(③).

## 3. 아키텍처 — 컴포넌트와 인터페이스

### 3.1 백엔드
- **오디오 서빙** `GET /api/v1/moments/{id}/audio`
  - `Photo.audio_path`의 파일을 스트리밍. `Content-Type`은 저장 확장자 기반(webm/m4a → audio/webm|audio/mp4), 없으면 404.
  - 앱 카드·공개 페이지 공용. 오디오 없는 순간은 404.
- **공개 순간 조회** `GET /api/v1/moments/{id}`
  - 반환: `{id, caption, transcript, emotion, project_title, image_url, audio_url, has_audio}`. 인증/localStorage 없음.
  - QR 목적지 페이지가 소비. 없는 id → 404(프론트가 친절 문구 처리).
- **인쇄 QR 합성** (renderer) — **위치: 사진 위 아님, 여백 밴드(2-b 결정)**
  - 사진 원본은 손대지 않는다. 내지용 이미지 = 원본 사진 + **하단에 종이색(`#F7F4EE`) 여백 밴드**를 덧댄 캔버스.
    그 밴드에 `PUBLIC_WEB_BASE + /v/{id}` QR(`qrcode`) + 작은 필름 라벨을 절제되게 배치(Pillow).
  - QR은 quiet-zone(흰 여백) 확보, 인쇄 시 스캔 가능 최소 크기(≈2cm+) 되도록 밴드 높이·QR 픽셀 산정.
  - Sweetbook 템플릿 변경 불필요 — 우리가 업로드하는 `photo` 이미지 자체를 "사진+QR밴드"로 만들어 보낸다.
    (템플릿이 별도 QR/이미지 슬롯을 지원하면 그걸 우선 — 오픈 아이템에서 Sandbox로 확인.)
  - 오디오 없는 순간은 밴드/QR 생략(원본 사진 그대로).
- **STT 튜닝** `stt.py`
  - `transcriptions.create(model="whisper-1", file=f, language="ko", prompt="여행 중 남긴 짧은 한국어 음성 메모")`.
  - 모델 상수는 CLAUDE.md 제약(`whisper-1`) 유지.
- **설정** `config.py`
  - `public_web_base: str = "http://localhost:5173"` (배포 시 실호스트). QR 목적지의 베이스.

### 3.2 프론트엔드
- **진짜 파형** `components/AudioWaveform.tsx` (기존 `Waveform.tsx` 대체/보강)
  - props: `src`(오디오 URL). fetch → `AudioContext.decodeAudioData` → 채널 데이터에서 N개 피크 산출 → 막대 렌더.
  - 재생 컨트롤: 탭하면 재생/일시정지, 진행에 따라 막대 앰버 채움(현재 시간/총 길이). `<audio>` 요소를 소스로 사용.
  - 디코드 실패/미지원 → 기본 막대(정적) + `<audio>` 네이티브 재생 폴백.
  - `prefers-reduced-motion` 존중.
- **MomentCard** — 가짜 seed 파형 → `AudioWaveform src={audioUrl}`. 탭 = 글귀 시트 + **실제 녹음 재생**.
- **공개 재생 페이지** `screens/Voice.tsx`, 라우트 `/v/:id` (App.tsx에 추가)
  - `getMoment(id)` → 사진 배경 + 명조 글귀 + 감정 칩 + `AudioWaveform` + 필름 스탬프. 필름/Retro 톤.
  - 없는 순간 → "이 순간은 더 이상 없어요." (친절 빈 상태)
- **api.ts** — `audioUrl(momentId)`, `getMoment(momentId)` 추가.

## 4. 데이터 모델
- 변경 **없음**(경량). `Photo.audio_path` 이미 존재, 파형은 클라이언트 계산, 공개 조회는 기존 필드 재사용.

## 5. 데이터 흐름
```
녹음 → uploadAudio → audio_path 저장 → (bg) Whisper(ko) 전사 → Haiku 캡션
앱 카드 탭 → GET /moments/{id}/audio → Web Audio decode → 진짜 파형 + 재생
주문 렌더 → per moment: QR(PUBLIC_WEB_BASE/v/{id}) 합성 → photo 이미지 업로드 → 인쇄
수령인 → 종이 QR 스캔 → /v/{id} → GET /moments/{id} → 명조 글귀 + 목소리 재생
```

## 6. 에러 처리
- 오디오 없음: 카드/페이지 플레이어 숨김, QR 생략. 글귀·사진만으로 성립(기존 불변식과 일관).
- 디코드 실패: `<audio>` 네이티브 폴백 + 정적 막대(침묵/크래시 금지).
- 없는/삭제된 순간(`/v/:id`): 404 → "이 순간은 더 이상 없어요."
- QR 생성 실패: 해당 순간만 QR 없이 인쇄(주문 전체는 진행).
- STT 실패/무음: 기존과 동일 — transcript 비움, 캡션 없이 진행.

## 7. 프라이버시
- 오디오·공개 페이지는 **추측 불가능한 UUID(moment id)** 로만 접근(Remento QR 모델). MVP 적정. 삭제 시 404.

## 8. 테스트 전략
- **유닛(백엔드)**: 오디오 엔드포인트(존재→200+content-type, 없음→404) · 공개 순간 응답 형태 · **QR 합성 이미지에서 URL 역디코드 성공**(qrcode 라운드트립) · STT 클라이언트가 `language="ko"` 전달(모킹).
- **프론트**: `api.ts` 유닛(audioUrl/getMoment 요청 조립). AudioWaveform은 Web Audio라 빌드 통과 + 수동/스크린샷.
- **통합**: 렌더러가 QR-합성 이미지를 업로드 경로에 태우는지(Sweetbook mock).

## 9. 필요한 것 / 설정
- `qrcode`(QR) — 백엔드 requirements 추가. Pillow는 이미 있음.
- `PUBLIC_WEB_BASE` 설정(.env, 기본 localhost).
- `ANTHROPIC_API_KEY`(캡션 실작동) — 사용자 env 작업. 없으면 캡션은 전사 원문 폴백.

## 10. 오픈 아이템(구현 중 확인)
- 인쇄 QR의 **스캔 가능 최소 크기 + 밴드 처리**: A5(148×210) 내지에서 "사진+하단 QR밴드" 이미지가 템플릿에 어떻게 앉는지(크롭/스케일), QR이 실제로 찍혀 스캔되는지 — 실 Sandbox 렌더 1건으로 눈 확인. 템플릿에 QR 전용 슬롯이 있으면 그쪽으로 전환.
- 오디오 mime/확장자: MediaRecorder가 브라우저별 webm/m4a → 서빙 Content-Type 매핑 표 확정.

## 11. 셀링 포인트 연결(포트폴리오)
- 기술: Web Audio 실파형 · 오디오 서빙 · QR 생성+공개 재생 페이지(디지털↔실물 브리지) · Whisper(ko)+Claude 파이프라인.
- 감정: 종이에서 진짜 목소리 재생 = 선물 전환 훅.
- 수익: QR/파형/음성 = Sweetbook 인쇄 프리미엄 업셀.
