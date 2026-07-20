from app.ai.parser import PageStreamParser


def test_parses_pages_across_chunks():
    p = PageStreamParser()
    out = []
    out += p.feed("<<<PAGE photo=abc>>>\n첫 페이")
    out += p.feed("지 글\n<<<PAGE photo=no")
    out += p.feed("ne>>>\n프롤로그 아님 막간\n")
    out += p.flush()
    assert [(x.photo_id, x.text) for x in out] == [
        ("abc", "첫 페이지 글"), (None, "프롤로그 아님 막간")]


def test_ignores_preamble_before_first_marker():
    p = PageStreamParser()
    out = p.feed("알겠습니다!\n<<<PAGE photo=x>>>\n본문") + p.flush()
    assert len(out) == 1 and out[0].photo_id == "x"
