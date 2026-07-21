"""DB 테이블 정의(Project/Photo=순간/Recipient). / 라우터와 AI 파이프라인이 호출. / db.Base를 사용."""
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
    cover_line: Mapped[str | None] = mapped_column(String, nullable=True)  # 표지 문구
    emotion_arc: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI 여행 감정 요약(사용자 캡션 기반)
    reveal_mode: Mapped[str] = mapped_column(String, default="slide")  # slide | dim (설계 3.5 A/B)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | ordered
    sweetbook_book_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sweetbook_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_status: Mapped[str | None] = mapped_column(String, nullable=True)
    photos: Mapped[list["Photo"]] = relationship(order_by="Photo.sort_order", cascade="all, delete-orphan")
    recipients: Mapped[list["Recipient"]] = relationship(cascade="all, delete-orphan")


class Photo(Base):
    """한 '순간' — 사진 + 음성 + 캡션 + 감정."""
    __tablename__ = "photos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    emotion: Mapped[str | None] = mapped_column(String, nullable=True)  # 사용자가 고른 감정 태그
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)  # 원본 음성
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)  # Whisper 전사 원문
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI 정리본(사용자 수정 가능)
    ai_scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)  # 감정 제안 근거(내부)
    suggested_emotion: Mapped[str | None] = mapped_column(String, nullable=True)  # AI가 제안한 감정
    analysis_status: Mapped[str] = mapped_column(String, default="pending")

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_path)


class Recipient(Base):
    """선물 수령인 — 주문 시 1명당 인쇄 1권."""
    __tablename__ = "recipients"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, default="")
    postal_code: Mapped[str | None] = mapped_column(String, nullable=True)  # Sweetbook 주문 필수
    gift_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sweetbook_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_status: Mapped[str | None] = mapped_column(String, nullable=True)


class Page(Base):
    """(v1 레거시) 집필 페이지 — 향후 제거. / writer.py가 아직 import하므로 스텁으로 유지."""
    __tablename__ = "pages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    photo_id: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    ai_text: Mapped[str] = mapped_column(Text)
    regen_count: Mapped[int] = mapped_column(Integer, default=0)
