"""오디오를 한국어로 전사한다.
caption 파이프라인이 부른다.
OpenAI Whisper를 쓴다.

무음이나 짧은 오디오에서 Whisper가 없는 문장을 지어내던 문제를 막는다.
프롬프트 힌트를 주지 않고, 세그먼트 신뢰도로 걸러 진짜 말이 없으면 빈 문자열을 돌려준다."""
from functools import lru_cache
import openai
from app.config import get_settings


@lru_cache
def get_stt_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=get_settings().openai_api_key or None)


def _seg_get(seg, key: str, default: float) -> float:
    v = seg.get(key) if isinstance(seg, dict) else getattr(seg, key, None)
    return default if v is None else float(v)


def _is_speech(seg) -> bool:
    # 확실한 무음만 버린다. 그 구간에서 Whisper가 없는 문장을 지어낸다.
    # 로그확률로는 거르지 않는다. 빠르거나 작은 실제 발화까지 잘려나간다.
    return _seg_get(seg, "no_speech_prob", 0.0) <= 0.85


def _seg_text(seg) -> str:
    return (seg.get("text") if isinstance(seg, dict) else getattr(seg, "text", "")) or ""


def transcribe(audio_path: str) -> str:
    """오디오를 한국어로 전사한다. 실제 말이 안 잡히면 지어내지 않고 빈 문자열을 돌려준다.
    프롬프트 힌트는 일부러 주지 않는다. 무음에서 없는 문장을 만들어내는 원인이었다."""
    with open(audio_path, "rb") as f:
        res = get_stt_client().audio.transcriptions.create(
            model="whisper-1", file=f, language="ko",
            response_format="verbose_json", temperature=0,
        )
    segs = getattr(res, "segments", None)
    if segs:
        return "".join(_seg_text(s) for s in segs if _is_speech(s)).strip()
    return (getattr(res, "text", "") or "").strip()
