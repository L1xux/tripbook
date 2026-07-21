import io
from PIL import Image


def _jpeg(color, size=(300, 300)):
    b = io.BytesIO(); Image.new("RGB", size, color).save(b, "JPEG"); return b.getvalue()


def test_compose_adds_band_and_qr():
    from app.sweetbook.renderer import compose_page_image
    out = compose_page_image(_jpeg((12, 12, 12)), "http://x/v/abc")
    img = Image.open(io.BytesIO(out))
    assert img.height > 300  # 하단 밴드가 추가됨
    band = img.crop((0, 300, img.width, img.height))
    colors = {c for _, c in (band.getcolors(maxcolors=200000) or [])}
    assert (255, 255, 255) in colors  # QR 흰 모듈 존재
    # 종이색 밴드(#F7F4EE) — JPEG 라운딩으로 채널당 ±3 허용
    assert any(abs(r - 247) <= 3 and abs(g - 244) <= 3 and abs(b - 238) <= 3
               for (r, g, b) in colors)
