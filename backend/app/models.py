"""DB 테이블 정의(Project/Photo/Page). / 라우터와 AI 파이프라인이 호출. / db.Base를 사용."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


def _uid() -> str:
    return uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    title: Mapped[str] = mapped_column(String)
    start_date: Mapped[str | None] = mapped_column(String, nullable=True)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    companions: Mapped[str | None] = mapped_column(String, nullable=True)
    mood: Mapped[str] = mapped_column(String)  # 무드 5종 enum 값
    status: Mapped[str] = mapped_column(String, default="draft")
    sweetbook_book_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sweetbook_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_status: Mapped[str | None] = mapped_column(String, nullable=True)
    photos: Mapped[list["Photo"]] = relationship(order_by="Photo.sort_order", cascade="all, delete-orphan")
    pages: Mapped[list["Page"]] = relationship(order_by="Page.page_number", cascade="all, delete-orphan")


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    emotion: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String, default="pending")
    user_scene_correction: Mapped[str | None] = mapped_column(Text, nullable=True)


class Page(Base):
    __tablename__ = "pages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    photo_id: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    ai_text: Mapped[str] = mapped_column(Text)
    regen_count: Mapped[int] = mapped_column(Integer, default=0)
