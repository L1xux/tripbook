"""DB 엔진/세션 관리. / 라우터들이 get_db로 호출. / SQLite 파일을 연다."""
import os
from contextlib import contextmanager
from fastapi import HTTPException
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


@contextmanager
def session_scope():
    """요청 밖(백그라운드 잡)에서 쓰는 세션 수명 관리. get_db의 잡 버전."""
    # 왜 SessionLocal을 매번 조회하는가: 테스트가 db_module.SessionLocal을 monkeypatch한다
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_404(db, model, id_: str, label: str):
    """모든 라우터가 공유하는 조회-또는-404. 라우터마다 재구현하지 않는다."""
    row = db.get(model, id_)
    if not row:
        raise HTTPException(404, f"{label} not found")
    return row
