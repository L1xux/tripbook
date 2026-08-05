"""DB 엔진과 세션 관리. / 라우터가 get_db로 호출. / SQLite 파일을 연다."""
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
    # 백그라운드 태스크가 다른 스레드에서 세션을 쓰므로 check_same_thread를 끈다
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
    """요청 밖에서 도는 백그라운드 잡이 쓰는 세션. get_db의 잡 버전이다."""
    # 테스트가 SessionLocal을 갈아끼우므로 매번 모듈에서 다시 찾는다
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_404(db, model, id_: str, label: str):
    """모든 라우터가 함께 쓰는 조회 후 404 처리."""
    row = db.get(model, id_)
    if not row:
        raise HTTPException(404, f"{label} not found")
    return row
