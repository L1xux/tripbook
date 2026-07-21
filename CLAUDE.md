# Tripbook — 프로젝트 규칙 (Claude Code용)

여행 사진+목소리를 AI가 캡션으로 다듬어 "순간"을 담고, Sweetbook Book Print API로
실물 책을 나 자신과 선물 수령인에게 주문하는 모바일 퍼스트 웹 서비스.

## 스택

- **백엔드**: Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite, anthropic SDK, openai SDK, httpx, Pillow, pytest
- **프론트엔드**: React 19 + TypeScript + Vite, react-router-dom, vitest (v2 프론트는 별도 계획(Plan B))
- **외부 API**: OpenAI(`gpt-4o-mini` — 사진 감정 제안 + 캡션 편집 + 감정 아크, Whisper `whisper-1` — 음성 전사),
  Sweetbook Book Print(TEMPLATE 방식). (anthropic SDK는 남아 있으나 현재 미사용 — LLM은 OpenAI로 통일.)

## 테스트 / 빌드 명령

```
cd backend;  python -m pytest tests/ -v          # 백엔드 전체 테스트
cd frontend; npm test                            # 프론트 테스트(vitest)
cd frontend; npm run build                       # 타입체크 + 빌드
cd backend;  python scripts/demo_e2e.py [--order]  # 로컬 E2E(uvicorn 실행 + 실키 필요)
```

## 모델 제약

- 캡션 편집·감정 제안·감정 아크 `gpt-4o-mini`(OpenAI), 음성 전사 Whisper `whisper-1`.
- 비전 감정 제안은 `response_format` json_schema(strict)로 `{scene, suggested_emotion}` 강제.
- API 키는 `.env`로만: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SWEETBOOK_API_KEY`, `SWEETBOOK_ENV=sandbox|live`.
  리포에는 `.env.example`만 커밋.

## 코드 규칙

- 모든 주요 모듈 상단에 3줄 docstring(한국어): "이 파일이 하는 일 / 누가 호출하는가 / 무엇을 호출하는가".
- 자명하지 않은 결정에만 "왜" 주석.
- 새 파일을 만들면 `docs/CODE_TOUR.md`에 1줄(역할 + "여기서 볼 것" 포인터) 추가.
- **캡션 불변식(창작 금지)**: 음성 캡션은 사용자가 말한 원문을 다듬을 뿐 새 사실·감정·인물·장소를
  추가하지 않는다(`app/ai/caption.py:NO_INVENTION`). 편집이 실패하면 전사 원문을 그대로 캡션으로 보존한다
  (침묵하거나 지어내지 않는다).

## 커밋 컨벤션

- Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`.
- 태스크(또는 논리 단위)마다 최소 1회 커밋.
