"""집필 스트림을 페이지 단위로 자르는 파서. / writer가 호출. / 표준 re만 사용."""
import re
from collections import namedtuple

ParsedPage = namedtuple("ParsedPage", "photo_id text")
_MARKER = re.compile(r"<<<PAGE photo=([A-Za-z0-9]+|none)>>>")


class PageStreamParser:
    def __init__(self):
        self._buf = ""
        self._current: str | None = None  # 현재 페이지의 photo_id ("none" 포함), 마커 전이면 None

    def _make(self, text: str) -> ParsedPage:
        pid = None if self._current == "none" else self._current
        return ParsedPage(pid, text.strip())

    def feed(self, chunk: str) -> list[ParsedPage]:
        self._buf += chunk
        done: list[ParsedPage] = []
        while True:
            m = _MARKER.search(self._buf)
            if not m:
                return done
            before = self._buf[: m.start()]
            if self._current is not None and before.strip():
                done.append(self._make(before))
            # 첫 마커 이전 텍스트(모델 잡담)는 버린다
            self._current = m.group(1)
            self._buf = self._buf[m.end():]

    def flush(self) -> list[ParsedPage]:
        if self._current is not None and self._buf.strip():
            out = [self._make(self._buf)]
            self._buf = ""
            return out
        return []
