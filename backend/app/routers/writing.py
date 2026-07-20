"""집필 시작/스트림 라우터. / main.py가 등록. / writer 태스크 실행, events 구독."""
import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.routers.projects import get_project_or_404
from app.ai.writer import run_writing
from app.events import bus

router = APIRouter(prefix="/api/v1", tags=["writing"])


@router.post("/projects/{project_id}/write", status_code=202)
async def start_writing(project_id: str, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    asyncio.create_task(run_writing(project_id))
    return {"started": True}


@router.get("/projects/{project_id}/write/stream")
async def stream(project_id: str, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)

    async def gen():
        q = bus.subscribe(project_id)
        try:
            while True:
                event = await q.get()
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["type"] in ("done", "error"):
                    return
        finally:
            bus.unsubscribe(project_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream")
