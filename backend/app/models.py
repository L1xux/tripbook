"""여행과 순간, 수령인 테이블을 정의한다.
라우터와 AI 파이프라인이 가져다 쓴다.
db.Base 위에 얹는다."""
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
    emotion_arc: Mapped[str | None] = mapped_column(Text, nullable=True)  # 사용자 글귀로 만든 여행 감정 요약
    reveal_mode: Mapped[str] = mapped_column(String, default="slide")  # slide 또는 dim
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | ordered
    sweetbook_book_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sweetbook_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_status: Mapped[str | None] = mapped_column(String, nullable=True)
    photos: Mapped[list["Photo"]] = relationship(order_by="Photo.sort_order", cascade="all, delete-orphan")
    recipients: Mapped[list["Recipient"]] = relationship(cascade="all, delete-orphan")


class Photo(Base):
    """한 순간. 사진과 음성, 글귀, 감정을 한 행에 묶는다."""
    __tablename__ = "photos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    emotion: Mapped[str | None] = mapped_column(String, nullable=True)  # 사용자가 고른 감정 태그
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)  # 원본 음성
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)  # Whisper가 옮긴 원문
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)  # 옮긴 말을 다듬은 캡션. 사용자가 고칠 수 있다
    ai_scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)  # 감정 제안의 근거. 화면에는 쓰지 않는다
    suggested_emotion: Mapped[str | None] = mapped_column(String, nullable=True)  # AI가 제안한 감정
    analysis_status: Mapped[str] = mapped_column(String, default="pending")

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_path)


class Recipient(Base):
    """선물 수령인. 주문할 때 한 명당 한 권을 인쇄한다."""
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
