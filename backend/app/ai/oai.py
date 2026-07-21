"""OpenAI 클라이언트 팩토리 + 모델 상수. / caption·analysis·arc가 호출. / config에서 키를 읽는다.
캡션 편집·사진 감정 제안·감정 아크를 gpt-4o-mini(저비용·비전·JSON 스키마)로 처리한다."""
from functools import lru_cache
from openai import OpenAI
from app.config import get_settings

CHAT_MODEL = "gpt-4o-mini"


# 왜 캐시하는가: 호출마다 새 클라이언트를 만들면 httpx 풀이 버려져 커넥션 재사용이 안 된다
@lru_cache
def get_oai_client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key or None)
