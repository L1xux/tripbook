"""OpenAI 클라이언트와 모델 상수를 둔다.
caption과 analysis, arc가 가져다 쓴다.
config에서 키를 읽는다.
캡션 편집과 감정 제안, 감정 아크를 모두 gpt-4o-mini로 처리한다."""
from functools import lru_cache
from openai import OpenAI
from app.config import get_settings

CHAT_MODEL = "gpt-4o-mini"


# 호출마다 새로 만들면 커넥션 풀이 버려지므로 캐시한다
@lru_cache
def get_oai_client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key or None)
