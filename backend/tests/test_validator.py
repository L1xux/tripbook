from app.ai.parser import ParsedPage
from app.ai.validator import validate_pages


def test_valid_pages_pass():
    pages = [ParsedPage(None, "프롤로그" * 40), ParsedPage("a", "본문" * 130), ParsedPage("b", "본문" * 130)]
    assert validate_pages(pages, ["a", "b"]) == []


def test_missing_and_duplicate_and_order_and_length():
    long = "글" * 260
    assert validate_pages([ParsedPage("a", long)], ["a", "b"])          # b 누락
    assert validate_pages([ParsedPage("a", long), ParsedPage("a", long)], ["a"])  # 중복
    assert validate_pages([ParsedPage("b", long), ParsedPage("a", long)], ["a", "b"])  # 순서
    assert validate_pages([ParsedPage("a", "짧다")], ["a"])              # 길이
