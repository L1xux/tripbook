"""책 조립 렌더러(TEMPLATE 방식). / orders 라우터가 호출. / SweetbookClient를 부른다.
BookRenderer 인터페이스 뒤에 격리 — 나중에 PdfRenderer를 끼울 수 있다(설계서 §8)."""
from typing import Protocol
from app.sweetbook.client import SweetbookClient


class BookRenderer(Protocol):
    def render(self, project, pages, spec: dict) -> str: ...


def build_cover_payload(project, spec: dict) -> dict:
    # 주의: 실제 템플릿 파라미터 스키마는 hello_book.py로 Sandbox에서 확정 후 조정
    return {"templateUid": spec.get("coverTemplateUid"), "params": {"title": project.title}}


def build_content_payload(page, spec: dict) -> dict:
    return {
        "templateUid": spec.get("contentTemplateUid"),
        "params": {"text": page.text, "photoId": page.photo_id},
    }


class TemplateRenderer:
    def __init__(self, client: SweetbookClient):
        self.client = client

    def render(self, project, pages, spec: dict) -> str:
        book = self.client.create_book({"creationType": "TEMPLATE", **{k: v for k, v in spec.items() if k == "bookSpecUid"}})
        book_uid = book["bookUid"]
        self.client.set_cover(book_uid, build_cover_payload(project, spec))
        for page in pages:
            self.client.add_content(book_uid, build_content_payload(page, spec))
        self.client.finalize(book_uid)
        return book_uid
