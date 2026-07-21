"""음성 전사(OpenAI Whisper). / caption 파이프라인이 호출. / openai SDK 사용."""
from functools import lru_cache
import openai
from app.config import get_settings


@lru_cache
def get_stt_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=get_settings().openai_api_key or None)


def transcribe(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        res = get_stt_client().audio.transcriptions.create(
            model="whisper-1", file=f, language="ko",
            prompt="여행 중 남긴 짧은 한국어 음성 메모",
        )
    return res.text.strip()
