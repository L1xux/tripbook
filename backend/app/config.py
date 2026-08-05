"""앱 전역 설정. / main.py와 외부 클라이언트 모듈이 호출. / .env 파일을 읽는다."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    sweetbook_api_key: str = ""
    sweetbook_env: str = "sandbox"  # sandbox | live
    # PUT /webhooks/config 등록 시 1회만 전체값이 내려오는 secretKey. 비어 있으면 서명 검증을 생략한다(로컬 전용).
    sweetbook_webhook_secret: str = ""
    data_dir: str = "data"
    database_url: str = "sqlite:///data/tripbook.db"
    public_web_base: str = "http://localhost:5173"  # 인쇄 QR이 가리킬 공개 웹 주소

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
