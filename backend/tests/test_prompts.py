from app.ai.prompts import MOOD_STYLES, build_system_prompt


def test_all_five_moods_have_styles():
    assert set(MOOD_STYLES) == {
        "family_essay", "friendship_saga", "fantasy_adventure", "lyrical_essay", "comedy"}


def test_system_prompt_contains_format_rules():
    s = build_system_prompt("fantasy_adventure")
    assert "<<<PAGE" in s and "250" in s
