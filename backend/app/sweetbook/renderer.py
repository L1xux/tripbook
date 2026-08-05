"""순간들을 한 권의 책으로 조립한다.
orders 라우터가 주문할 때 부른다.
SweetbookClient를 쓴다.
create에서 title이 필수이고, cover와 contents는 multipart로 사진을 올린다.
BookRenderer 뒤에 두어 나중에 PDF 방식 렌더러로 갈아끼울 수 있게 했다."""
import io
import qrcode
from PIL import Image
from typing import Protocol
from app.config import get_settings
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


def compose_page_image(photo_bytes: bytes, url: str, band_ratio: float = 0.18) -> bytes:
    """사진 아래에 종이색 밴드를 덧대고 그 안에 QR을 넣는다. 사진 원본 픽셀은 건드리지 않는다."""
    base = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    w, h = base.size
    band = int(h * band_ratio)
    canvas = Image.new("RGB", (w, h + band), (247, 244, 238))  # 종이색 #F7F4EE
    canvas.paste(base, (0, 0))
    qr = qrcode.make(url).convert("RGB")               # 여백을 포함해 스캔이 잘 되게 한다
    qs = int(band * 0.82)
    qr = qr.resize((qs, qs))
    canvas.paste(qr, (w - qs - int(band * 0.12), h + (band - qs) // 2))
    out = io.BytesIO(); canvas.save(out, "JPEG", quality=90)
    return out.getvalue()


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

        # 표지에는 첫 순간의 원본 사진과 제목, 문구, 여행 기간이 들어간다
        self.client.set_cover(
            book_uid, spec.get("coverTemplateUid"),
            {"title": project.title, "coverLine": getattr(project, "cover_line", None) or project.title,
             "dateRange": date_range(project), "coverPhoto": "$upload"},
            {"coverPhoto": ("cover.jpg", _image(moments[0].file_path), "image/jpeg")})

        content_uid = spec.get("contentTemplateUid")
        count = 0
        # 순간 하나가 내지 한 페이지가 된다
        web_base = get_settings().public_web_base
        for m in moments:
            img = _image(m.file_path)
            if getattr(m, "audio_path", None):  # 목소리가 담긴 순간에만 QR 밴드를 넣는다
                img = compose_page_image(img, f"{web_base}/v/{getattr(m, 'id', '')}")
            r = self.client.add_content(
                book_uid, content_uid,
                {"caption": getattr(m, "caption", None) or "", "photo": "$upload"},
                {"photo": ("p.jpg", img, "image/jpeg")}, break_before="page")
            count = r.get("pageMeta", {}).get("currentPageCount", count + 1)

        # 판형 최소 페이지에 못 미치면 마지막 사진으로 여백을 채워 최종화를 통과시킨다.
        # 지금은 임시 방편이고 나중에 빈 페이지 템플릿으로 대체한다.
        while count < page_min:
            r = self.client.add_content(
                book_uid, content_uid, {"caption": "", "photo": "$upload"},
                {"photo": ("p.jpg", _image(moments[-1].file_path), "image/jpeg")}, break_before="page")
            new = r.get("pageMeta", {}).get("currentPageCount", count + 1)
            count = new if new > count else count + 1  # 응답이 페이지 수를 안 주더라도 루프가 끝나게 한다

        self.client.finalize(book_uid)
        return book_uid
