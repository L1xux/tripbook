# 코드 투어 — 읽는 순서대로

처음 보는 사람이 이 순서로 파일을 열면 시스템 전체가 이해되도록 배치했다.
각 파일 상단에는 "이 파일이 하는 일 / 누가 호출하는가 / 무엇을 호출하는가" 3줄 docstring이 있다.

## 기반 (설정 · DB · 모델)

1. `backend/app/main.py` — 앱 조립(엔트리포인트). 여기서 시작하세요. **여기서 볼 것:** `create_app()`이 등록하는 라우터 목록 = 기능 지도.
2. `backend/app/config.py` — `.env` 설정 로딩(`get_settings()`). **여기서 볼 것:** ANTHROPIC/SWEETBOOK 키가 어디서 오는지.
3. `backend/app/db.py` — DB 엔진/세션(`Base`, `SessionLocal`, `get_db`). **여기서 볼 것:** `check_same_thread=False`인 이유(백그라운드 태스크).
4. `backend/app/models.py` — DB 테이블(Project/Photo/Page). **여기서 볼 것:** status/analysis_status 상태 문자열, 원본/리사이즈 분리를 떠받치는 필드.
5. `backend/app/schemas.py` — 요청/응답 Pydantic 스키마. **여기서 볼 것:** `Mood` Literal 5종, `ProjectOut`이 photos/pages를 함께 내려주는 구조.

## API 라우터 (요청 진입점)

6. `backend/app/routers/projects.py` — 프로젝트 생성/조회. **여기서 볼 것:** `get_project_or_404`(다른 라우터가 공용으로 씀).
7. `backend/app/routers/photos.py` — 사진 업로드/수정/정렬. **여기서 볼 것:** 원본+리사이즈 저장, EXIF 촬영일 초기 정렬, 분석 BackgroundTasks 시작.
8. `backend/app/routers/writing.py` — 집필 시작 + SSE 스트림. **여기서 볼 것:** `asyncio.create_task(run_writing)`와 이벤트 버스 구독 제너레이터.
9. `backend/app/routers/pages.py` — 페이지 수정/재생성. **여기서 볼 것:** 재생성이 앞/뒤 페이지를 문맥으로 넘기는 방식.
10. `backend/app/routers/orders.py` — 주문 생성/상태/웹훅. **여기서 볼 것:** status가 "ready"일 때만 주문, SweetbookError → 502 매핑.

## AI 파이프라인

11. `backend/app/ai/llm.py` — Anthropic 클라이언트 팩토리+모델 상수. **여기서 볼 것:** lru_cache로 커넥션 풀 재사용, analysis/writer/regen이 공유.
12. `backend/app/ai/prompts.py` — 집필 프롬프트 조립(무드 5종). **여기서 볼 것:** `FORMAT_RULES`의 `<<<PAGE>>>` 규격.
12. `backend/app/ai/parser.py` — 스트림 출력을 페이지 단위로 파싱. **여기서 볼 것:** 청크 경계를 넘는 마커 처리, 첫 마커 이전 잡담 폐기.
13. `backend/app/ai/validator.py` — 파싱된 페이지 검증(사진 매칭/순서/길이). **여기서 볼 것:** 250~400자, 사진당 정확히 1페이지 규칙.
14. `backend/app/ai/writer.py` — 집필 잡: Opus 스트림→파서→DB+SSE, 검증 실패 시 1회 재시도. **여기서 볼 것:** 재시도 전 오류를 프롬프트에 되먹이는 부분.
15. `backend/app/ai/analysis.py` — 사진 비전 분석(Haiku 4.5 structured outputs). **여기서 볼 것:** 리사이즈본(_small.jpg) 사용, scene 1문장+전체 JSON 저장.
16. `backend/app/ai/regen.py` — 페이지 단위 재생성(Opus). **여기서 볼 것:** 무드 스타일 재사용, regen_count 증가.
17. `backend/app/imaging.py` — 이미지 리사이즈+EXIF 촬영일 추출. **여기서 볼 것:** MAX_EDGE=1100 선택 이유(비전 토큰 절감).
18. `backend/app/events.py` — 프로젝트별 SSE 이벤트 버스(인메모리 asyncio.Queue). **여기서 볼 것:** publish/subscribe/unsubscribe.

## Sweetbook 연동

19. `backend/app/sweetbook/client.py` — Book Print API HTTP 클라이언트. **여기서 볼 것:** `{success, data, errors}` 언랩, transport 주입(테스트 모킹).
20. `backend/app/sweetbook/renderer.py` — 책 조립 렌더러(create→cover→contents→finalize). **여기서 볼 것:** payload 조립을 `build_*_payload`로 분리해 스키마 변경을 국소화.

## 프론트엔드 (모바일 퍼스트 위자드)

21. `frontend/src/api.ts` — 백엔드 API 클라이언트. **여기서 볼 것:** 모든 컴포넌트는 이 파일로만 서버와 통신, 에러 detail을 사용자 메시지로 변환.
22. `frontend/src/utils.ts` — 공용 유틸(patchById). **여기서 볼 것:** Step2/Step4의 리스트 패치가 이 하나를 공유.
23. `frontend/src/App.tsx` — 라우터 + 위자드 5단계 연결.
23. `frontend/src/steps/Step1Info.tsx` — 여행 정보 + 무드 선택.
24. `frontend/src/steps/Step2Photos.tsx` — 사진 업로드 + 메모 + AI 장면 교정 + 순서 조정(분석 폴링).
25. `frontend/src/steps/Step3Writing.tsx` — 실시간 집필 피드(EventSource SSE).
26. `frontend/src/steps/Step4Review.tsx` — 퇴고(수정 + 재생성).
27. `frontend/src/steps/Step5Order.tsx` — 배송 입력 + 주문 + 상태 폴링.
