"""Anthropic 클라이언트 팩토리+공용 상수. / analysis·writer·regen이 호출. / config에서 키를 읽는다."""
from functools import lru_cache
import anthropic
from app.config import get_settings

ANALYSIS_MODEL = "claude-haiku-4-5"
WRITER_MODEL = "claude-opus-4-8"
ADAPTIVE_THINKING = {"type": "adaptive"}


# 왜 캐시하는가: 호출마다 새 클라이언트를 만들면 httpx 풀이 버려져 TCP/TLS 재사용이 안 된다
@lru_cache
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key or None)


@lru_cache
def get_async_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key or None)


def first_text(res) -> str:
    """응답 content 블록에서 첫 텍스트를 꺼낸다 (thinking 블록 건너뜀)."""
    return next(b.text for b in res.content if b.type == "text")
