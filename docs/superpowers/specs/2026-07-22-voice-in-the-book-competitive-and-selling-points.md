# Tripbook 한방 결정 & 경쟁 리서치 & 포트폴리오 셀링 포인트

> 작성 2026-07-22. 목적: 포트폴리오(스위트북 입사 지원)로서 "한방(wow factor)"이 없다는 문제를
> 경쟁 서비스 리서치로 진단하고, **THE 시그니처 = "목소리가 실물 책에 산다"** 로 확정한 근거·셀링 포인트를 남긴다.
> 이 문서는 이후 설계 스펙(`2026-07-22-voice-in-the-book-design.md`, 예정)의 근거 문서다.

## 결정 (2026-07-22)

**THE 한방 = ① 목소리가 실물 책에 산다 (Voice lives in the book).**
- 앱: 순간 카드 탭 → **내 실제 녹음 재생** + **진짜 음성 파형**(Web Audio, 지금은 가짜 sin() 파형).
- 책: 순간마다 인쇄면에 **QR/파형** → 스캔하면 **그때 그 목소리 원본이 재생**. "읽으면서 동시에 그때 목소리를 듣는다."
- 로드맵 2·3순위: ② 감정 리마인드(시간이 지나 되돌려주기), ⑤ in-trip 캡처(여행 중 순간 계속 담기), ③ 여러 목소리 한 권(협업).

이 결정이 사용자의 3대 불만(소리 안 남 · 파형이 가짜 · AI가 안 느껴짐)을 한 번에 해소하고,
포트폴리오의 **기술 임팩트 + 감정 임팩트**를 동시에 잡는다.

## 카테고리의 한방은 이미 수렴돼 있다 — "진짜 목소리를 실물에 각인"

- **Remento** (Shark Tank, 이 분야 최강 레퍼런스): 인쇄 하드커버 각 챕터에 **QR코드 → 원본 음성 재생**.
  "Speech-to-Story"로 필러워드만 제거하고 다듬되 원하면 verbatim 보존(= 우리 `NO_INVENTION` 불변식과 동일 철학).
  수익모델 **$99 단건**(무제한 녹음 + 하드커버 1권 + 평생 디지털 아카이브), 주간 프롬프트·가족 협업이 리텐션 엔진.
  포지셔닝: 어르신 유산 기록 + 선물(gifting) 이중 타깃.
  · https://www.remento.co/ · https://www.remento.co/how-it-works
- **Positive Prints — Soundwave Art**: 실제 목소리로 만든 **인쇄 파형 + QR 재생**을 포스터·액자·주얼리·디지털로 판매.
  "대체 불가한 목소리"를 감정 훅으로, 상실·그리움 카피로 구매 유도. → 파형+음성이 **팔리는 상품**이라는 증거.
  · https://positiveprints.com/product/memorial-voice-recording-soundwave-art/
- **QRVoice / The Voice Library**: 음성을 QR로 담아 재생(약 3초~). QR-음성 메커닉이 **저비용으로 구현 가능**함을 확인.
  단, AI 편집·감성 디자인 없이 QR만 얹으면 "허접"으로 읽힘(저가 대조군).
  · https://www.thevoicelibrary.net/ · https://play.google.com/store/apps/details?id=app.tacram.qrvoice

## 인접 벤치마크

- **Rosebud** (AI 감정 저널링): 음성/텍스트 → AI가 **감정 패턴·트리거 추출**, 주간 "감정 지형(emotional landscape)"으로
  되돌려줌. 데이터로 감동 증명("한 주 만에 불안 69% 개선"). 프리미엄 Bloom $8.99/월. → 우리 ②(감정 리마인드)의 정석.
  · https://www.rosebud.app/
- **Day One**: 사진·음성에 날씨·위치·음악 메타데이터 자동 기록, **On This Day**로 과거 순간 재소환. $34.99/년. E2E 암호화=신뢰 신호.
  · https://dayoneapp.com/ · https://dayoneapp.com/plans/
- **Storyworth**: 이메일/타이핑 기반 회고록 $99/년 — **글쓰기 장벽**이 있는 쪽. 목소리-우선이 "매직"을 만든다는 대조.
  · https://welcome.storyworth.com/storyworth-vs-remento
- **Artifact Uprising**: Mohawk 제지·foil stamping·fabric binding 등 **재료·크래프트**로 프리미엄 증명. 실물의 촉감을 카피로 판다.
  · https://www.artifactuprising.com/
- **한국**: 레포브(온보딩·아카이브 경험으로 프리미엄 인식), 퍼블로그(포토북→300+ 굿즈 확장·당일배송),
  스냅스/포토몬(레이플랫 품질·가격 기대선: 하드 레이플랫 21p ≈ 2.5만원, 소프트 32p ≈ 3.1만원), 클로바노트(한국어 STT 표준),
  무디(감정 키워드+BGM 몰입). → 한국 소비자의 품질·감성 기대선.
  · https://apps.apple.com/kr/app/id6502975294 · https://www.publog.co.kr/ · https://theqoo.net/review/1747871281

## 왜 지금 "허접해 보이나" (프리미엄 vs 아마추어 — 리서치 기반)

- **여백**: 화면/페이지를 꽉 채우면 아마추어. 사진에 숨 쉴 공간을 줘야 프리미엄(Artifact Uprising, 커스텀 포토북 비교).
- **AI가 안 보임**: Rosebud처럼 AI 결과를 **감동으로 되돌려줘야** 한다. 우리는 Haiku 감정 제안을 화면에 안 띄워 AI가 없는 듯 보임.
- **완성도 신호**(Affective): 커스텀 아이콘 vs 스톡, 일관된 stroke/코너, 깊은 색(navy/burgundy)=고급 / 밝은 채도=저렴,
  마이크로카피는 "기능 설명 말고 보여줘라"(Reserve Yours/Join the Circle), 애니메이션은 **눈치 못 챌 만큼** 자연스럽게.
  · https://weareaffective.com/learning-centre/what-makes-a-mobile-app-feel-premium-and-exclusive
- **타이포**(Toptal): 본문 line-height 1.4~1.6, leading을 사이즈보다 2~5pt 크게 — 답답한 행간이 허접함을 만든다.
- **실물 품질**(더쿠 후기): 한국 소비자는 레이플랫·페이지 완성도·가격을 냉정하게 본다. 우리 책이 이 기대선을 넘어야 함.

## 포트폴리오 셀링 포인트 (크래프트 대상 — 계속 다듬는다)

**한 줄 훅:** "종이책을 펼치면, 그때 내 목소리가 흘러나온다."

1. **감정 한방 — 대체 불가한 목소리.** 사진은 그때를 보여주지만 목소리는 그때를 *되살린다*. 종이에서 진짜 목소리가
   재생되는 순간이 눈물버튼이자 **선물 전환**의 핵심(선물은 지불의사가 높다).
2. **기술 임팩트(채용 심사용).** 단순 CRUD를 넘어: Web Audio 실시간 파형 · 오디오 저장/스트리밍 서빙 ·
   QR 생성 + **공개 음성 재생 페이지**(디지털↔실물 브리지) · Whisper 전사 + Claude 캡션(**창작 금지 불변식**) +
   사진 감정분석 파이프라인 · Sweetbook 실연동(멀티파트 렌더 + 다인수 주문). "감성 제품 + 진짜 엔지니어링"을 동시 증명.
3. **수익 직결.** QR/파형/음성 = Sweetbook 인쇄 매출의 **프리미엄 업셀**이자 새 수요 깔때기. 앱의 모든 주문 = 스위트북 매출.
4. **차별화 vs Remento.** Remento는 인터뷰·유산(어르신 대상, 주간 프롬프트). Tripbook은 **여행·그 현장의 순간**(젊은 층,
   현장 셀프 캡처, 감정 태그). 같은 "목소리를 각인" 훅을 **여행 세그먼트**로 가져온 게 우리 포지션.
5. **국내 맥락 적합.** 한국은 기록 열풍(Z세대) + 포토북 시장 성숙 + 클로바노트로 음성 기록에 익숙 → 한국어 STT 튜닝과
   명조 글귀 + 앰버 파형의 감성 코드가 잘 맞는다.

## 남은 갭(이 한방과 함께 메꿀 것)

- 진짜 음성 재생 + 진짜 파형(현재 가짜 sin()), 오디오 서빙 엔드포인트 부재
- 인쇄면 QR + 공개 재생 페이지(신규)
- AI 감정 제안 UI 노출(현재 숨김), STT 한국어 튜닝(`language="ko"` 등)
- ANTHROPIC_API_KEY 비어 있어 캡션 파이프라인 미작동
- in-trip 캡처(여행 중 순간 추가) — 앨범에서 순간 추가 UI 부재

## 출처 (리서치 수집분, 2026-07-22)

Remento(.co, /how-it-works) · Storyworth(vs-remento) · Positive Prints(soundwave-art) · The Voice Library ·
QRVoice · Rosebud · Day One(app, /plans) · Artifact Uprising · Affective(premium, animation) · Toptal(typography) ·
Justinmind(microcopy) · Arounda(typography) · WellAlly(Whisper voice journal) · arXiv 2407.21315 / 2504.12867(음성 감정) ·
고구마팜(Z세대 기록앱) · 더쿠(포토북 후기) · 레포브(App Store) · 퍼블로그 · 클로바노트.
