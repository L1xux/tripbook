"""집필 잡: Opus 스트림→파서→DB+SSE. / writing 라우터가 태스크로 실행. / prompts·parser·validator·events 사용."""
from typing import AsyncIterator
import app.db as db_module
from app.models import Project, Page
from app.ai.llm import ADAPTIVE_THINKING, WRITER_MODEL, get_async_client
from app.ai.prompts import build_system_prompt, build_user_prompt
from app.ai.parser import PageStreamParser, ParsedPage
from app.ai.validator import validate_pages
from app.events import bus


async def stream_book_text(system: str, user: str) -> AsyncIterator[str]:
    async with get_async_client().messages.stream(
        model=WRITER_MODEL,
        max_tokens=64000,
        thinking=ADAPTIVE_THINKING,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


def _clear_pages(db, project: Project) -> None:
    for old in list(project.pages):
        db.delete(old)
    db.commit()


def _emit_page(db, project_id: str, number: int, page: ParsedPage) -> None:
    """페이지 저장 + SSE 발행. 이벤트 형태는 여기 한 곳에서만 정의한다."""
    row = Page(project_id=project_id, page_number=number, photo_id=page.photo_id,
               text=page.text, ai_text=page.text)
    db.add(row); db.commit(); db.refresh(row)
    bus.publish(project_id, {"type": "page", "id": row.id,
                             "page_number": row.page_number,
                             "photo_id": row.photo_id, "text": row.text})


async def run_writing(project_id: str) -> None:
    with db_module.session_scope() as db:
        project = db.get(Project, project_id)
        project.status = "writing"
        _clear_pages(db, project)  # 재집필 시 기존 페이지 제거
        photos = project.photos
        system = build_system_prompt(project.mood)
        user = build_user_prompt(project, photos)
        photo_ids = [p.id for p in photos]

        for attempt in range(2):  # 검증 실패 시 1회 재시도
            parser = PageStreamParser()
            pages: list[ParsedPage] = []
            try:
                async for chunk in stream_book_text(system, user):
                    for done in parser.feed(chunk):
                        pages.append(done)
                        _emit_page(db, project_id, len(pages), done)
                for done in parser.flush():
                    pages.append(done)
                    _emit_page(db, project_id, len(pages), done)
            except Exception as e:
                project.status = "draft"; db.commit()
                bus.publish(project_id, {"type": "error", "message": f"집필 중단: {e}"})
                return
            errors = validate_pages(pages, photo_ids)
            if not errors:
                project.status = "ready"; db.commit()
                bus.publish(project_id, {"type": "done"})
                return
            # 재시도 전에 이번 시도의 페이지를 지우고, 오류를 프롬프트에 명시
            _clear_pages(db, project)
            user = build_user_prompt(project, photos) + "\n\n이전 시도의 오류를 반드시 고쳐라:\n- " + "\n- ".join(errors)
        project.status = "draft"; db.commit()
        bus.publish(project_id, {"type": "error", "message": "검증 실패: " + "; ".join(errors)})
