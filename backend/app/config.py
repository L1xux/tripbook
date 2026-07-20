"""앱 전역 설정. / main.py와 외부 클라이언트 모듈이 호출. / .env 파일을 읽는다."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    sweetbook_api_key: str = ""
    sweetbook_env: str = "sandbox"  # sandbox | live
    data_dir: str = "data"
    database_url: str = "sqlite:///data/tripbook.db"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
