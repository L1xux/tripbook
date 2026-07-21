"""책 조립 렌더러(TEMPLATE 방식). / orders 라우터가 호출. / SweetbookClient를 부른다.
BookRenderer 인터페이스 뒤에 격리 — 나중에 PdfRenderer를 끼울 수 있다(설계서 §8)."""
from typing import Protocol
from app.sweetbook.client import SweetbookClient


class BookRenderer(Protocol):
    def render(self, project, pages, spec: dict) -> str: ...


def build_cover_payload(project, spec: dict) -> dict:
    return {"templateUid": spec.get("coverTemplateUid"),
            "params": {"title": project.title, "coverLine": getattr(project, "cover_line", None)}}


def build_content_payload(moment, spec: dict) -> dict:
    # 한 순간 = 한 페이지: 사진 + 캡션(사용자의 말)
    return {"templateUid": spec.get("contentTemplateUid"),
            "params": {"photoId": getattr(moment, "id", None), "caption": getattr(moment, "caption", None) or ""}}


class TemplateRenderer:
    def __init__(self, client: SweetbookClient):
        self.client = client

    def render(self, project, pages, spec: dict) -> str:
        create = {"creationType": "TEMPLATE"}
        if "bookSpecUid" in spec:
            create["bookSpecUid"] = spec["bookSpecUid"]
        book = self.client.create_book(create)
        book_uid = book["bookUid"]
        self.client.set_cover(book_uid, build_cover_payload(project, spec))
        for page in pages:
            self.client.add_content(book_uid, build_content_payload(page, spec))
        self.client.finalize(book_uid)
        return book_uid
