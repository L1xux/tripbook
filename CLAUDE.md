# Tripbook — 프로젝트 규칙 (Claude Code용)

여행 사진+메모를 AI가 여행기로 집필하고 Sweetbook Book Print API로 실물 책을 주문하는
모바일 퍼스트 웹 서비스.

## 스택

- **백엔드**: Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite, anthropic SDK, httpx, Pillow, pytest
- **프론트엔드**: React 19 + TypeScript + Vite, react-router-dom, vitest
- **외부 API**: Claude(Haiku 4.5 사진 분석, Opus 4.8 집필/재생성), Sweetbook Book Print(TEMPLATE 방식)

## 테스트 / 빌드 명령

```
cd backend;  python -m pytest tests/ -v          # 백엔드 전체 테스트
cd frontend; npm test                            # 프론트 테스트(vitest)
cd frontend; npm run build                       # 타입체크 + 빌드
cd backend;  python scripts/demo_e2e.py [--order]  # 로컬 E2E(uvicorn 실행 + 실키 필요)
```

## 모델 제약

- 사진 분석 `claude-haiku-4-5`, 집필/재생성 `claude-opus-4-8`(thinking adaptive).
- `budget_tokens` / `temperature`는 쓰지 말 것(400 오류).
- API 키는 `.env`로만: `ANTHROPIC_API_KEY`, `SWEETBOOK_API_KEY`, `SWEETBOOK_ENV=sandbox|live`.
  리포에는 `.env.example`만 커밋.

## 코드 규칙

- 모든 주요 모듈 상단에 3줄 docstring(한국어): "이 파일이 하는 일 / 누가 호출하는가 / 무엇을 호출하는가".
- 자명하지 않은 결정에만 "왜" 주석.
- 새 파일을 만들면 `docs/CODE_TOUR.md`에 1줄(역할 + "여기서 볼 것" 포인터) 추가.
- 무드 5종 enum: `family_essay | friendship_saga | fantasy_adventure | lyrical_essay | comedy`.
- 페이지 텍스트 250~400자. 모든 사진은 순서대로 정확히 1페이지. 창작 페이지는 photo 없음.

## 커밋 컨벤션

- Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`.
- 태스크(또는 논리 단위)마다 최소 1회 커밋.
