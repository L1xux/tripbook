"""요청/응답 Pydantic 스키마. / 라우터가 호출. / models와 필드가 대응."""
from typing import Literal
from pydantic import BaseModel

Mood = Literal["family_essay", "friendship_saga", "fantasy_adventure", "lyrical_essay", "comedy"]


class ProjectCreate(BaseModel):
    title: str
    mood: Mood
    start_date: str | None = None
    end_date: str | None = None
    companions: str | None = None


class PhotoOut(BaseModel):
    id: str
    sort_order: int
    emotion: str | None
    note: str | None
    ai_scene_description: str | None
    analysis_status: str
    user_scene_correction: str | None
    scene: str | None = None  # models.Photo.scene 프로퍼티 — UI가 문자열 파싱하지 않게 서버가 준다
    model_config = {"from_attributes": True}


class PageOut(BaseModel):
    id: str
    page_number: int
    photo_id: str | None
    text: str
    regen_count: int
    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: str
    title: str
    mood: str
    status: str
    start_date: str | None
    end_date: str | None
    companions: str | None
    order_status: str | None
    photos: list[PhotoOut]
    pages: list[PageOut]
    model_config = {"from_attributes": True}
