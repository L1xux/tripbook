"""책 조립 렌더러(TEMPLATE 방식). / orders 라우터가 호출. / SweetbookClient를 부른다.
create(title 필수) → cover(coverPhoto multipart) → contents(순간마다 breakBefore=page) → finalize(pageMin 충족).
BookRenderer 인터페이스 뒤에 격리 — 나중에 PdfRenderer를 끼울 수 있다(설계서 §8)."""
from typing import Protocol
from app.sweetbook.client import SweetbookClient


class BookRenderer(Protocol):
    def render(self, project, moments, spec: dict) -> str: ...


def date_range(project) -> str:
    a, b = getattr(project, "start_date", None), getattr(project, "end_date", None)
    if a and b:
        return f"{a} – {b}"
    return a or b or ""


def _image(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


class TemplateRenderer:
    def __init__(self, client: SweetbookClient):
        self.client = client

    def render(self, project, moments, spec: dict) -> str:
        if not moments:
            raise ValueError("순간이 없는 책은 렌더할 수 없습니다")
        book = self.client.create_book({
            "creationType": "TEMPLATE", "bookSpecUid": spec.get("bookSpecUid"), "title": project.title})
        book_uid = book["bookUid"]
        page_min = book.get("pageMeta", {}).get("pageMin", 0)

        # 표지 — 첫 순간의 인쇄용 원본 사진 + 제목/문구/여행기간
        self.client.set_cover(
            book_uid, spec.get("coverTemplateUid"),
            {"title": project.title, "coverLine": getattr(project, "cover_line", None) or project.title,
             "dateRange": date_range(project), "coverPhoto": "$upload"},
            {"coverPhoto": ("cover.jpg", _image(moments[0].file_path), "image/jpeg")})

        content_uid = spec.get("contentTemplateUid")
        count = 0
        # 순간 1개 = 내지 1페이지 (한 순간이 곧 한 펼침면의 글귀+사진)
        for m in moments:
            r = self.client.add_content(
                book_uid, content_uid,
                {"caption": getattr(m, "caption", None) or "", "photo": "$upload"},
                {"photo": ("p.jpg", _image(m.file_path), "image/jpeg")}, break_before="page")
            count = r.get("pageMeta", {}).get("currentPageCount", count + 1)

        # 판형 최소 페이지(예: 스퀘어북 24p) 미달이면 마지막 사진으로 여백 페이지를 채워 finalize를 통과시킨다.
        # (MVP 정책 — 추후 표지 뒤 간지/빈 페이지 템플릿으로 대체)
        while count < page_min:
            r = self.client.add_content(
                book_uid, content_uid, {"caption": "", "photo": "$upload"},
                {"photo": ("p.jpg", _image(moments[-1].file_path), "image/jpeg")}, break_before="page")
            new = r.get("pageMeta", {}).get("currentPageCount", count + 1)
            count = new if new > count else count + 1  # 응답이 카운트를 안 주면 진행 보장

        self.client.finalize(book_uid)
        return book_uid
