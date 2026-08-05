"""요청과 응답 스키마. / 라우터가 호출. / models의 필드와 대응한다."""
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    start_date: str | None = None
    end_date: str | None = None
    companions: str | None = None
    cover_line: str | None = None


class MomentOut(BaseModel):
    id: str
    sort_order: int
    emotion: str | None
    note: str | None
    caption: str | None
    transcript: str | None
    suggested_emotion: str | None
    analysis_status: str
    has_audio: bool
    model_config = {"from_attributes": True}


class RecipientOut(BaseModel):
    id: str
    name: str
    phone: str | None
    address: str
    postal_code: str | None
    gift_message: str | None
    order_status: str | None
    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: str
    title: str
    status: str
    cover_line: str | None
    emotion_arc: str | None
    reveal_mode: str
    start_date: str | None
    end_date: str | None
    companions: str | None
    order_status: str | None
    photos: list[MomentOut]
    recipients: list[RecipientOut]
    model_config = {"from_attributes": True}


PhotoOut = MomentOut  # 옛 라우터가 쓰던 이름
