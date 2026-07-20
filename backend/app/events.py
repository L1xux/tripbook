"""프로젝트별 SSE 이벤트 버스(인메모리). / writer가 publish, writing 라우터가 subscribe. / asyncio.Queue 사용."""
import asyncio


class EventBus:
    def __init__(self):
        self._subs: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, project_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.setdefault(project_id, []).append(q)
        return q

    def unsubscribe(self, project_id: str, q: asyncio.Queue):
        self._subs[project_id].remove(q)

    def publish(self, project_id: str, event: dict):
        for q in self._subs.get(project_id, []):
            q.put_nowait(event)


bus = EventBus()
