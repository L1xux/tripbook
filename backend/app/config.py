"""앱 전역 설정. / main.py와 외부 클라이언트 모듈이 호출. / .env 파일을 읽는다."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    sweetbook_api_key: str = ""
    sweetbook_env: str = "sandbox"  # sandbox | live
    # 웹훅 등록 때 한 번만 내려오는 secretKey. 비어 있으면 서명 검증을 생략하므로 로컬에서만 비워 둔다.
    sweetbook_webhook_secret: str = ""
    # 우리가 파는 책 한 종류. 판형과 템플릿 uid의 단일 출처다.
    # 단가는 여기 두지 않고 GET /book-specs로 계약 단가를 그때그때 받아온다.
    sweetbook_book_spec_uid: str = "SQUAREBOOK_HC"        # 고화질 스퀘어북 하드커버
    sweetbook_cover_template_uid: str = "79yjMH3qRPly"    # 일기장A 표지. taupe 명조로 우리 디자인과 맞는다
    sweetbook_content_template_uid: str = "2mi1ao0Z4Vxl"  # 공용 빈내지
    data_dir: str = "data"
    database_url: str = "sqlite:///data/tripbook.db"
    public_web_base: str = "http://localhost:5173"  # 인쇄 QR이 가리킬 공개 웹 주소

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
