"""DB 엔진/세션 관리. / 라우터들이 get_db로 호출. / SQLite 파일을 연다."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    settings = get_settings()
    url = url or settings.database_url
    if url.startswith("sqlite:///"):
        os.makedirs(os.path.dirname(url.replace("sqlite:///", "")) or ".", exist_ok=True)
    # 왜 check_same_thread=False: FastAPI 백그라운드 태스크가 다른 스레드에서 세션을 쓴다
    return create_engine(url, connect_args={"check_same_thread": False})


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def init_db(target=None):
    Base.metadata.create_all(target or engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
