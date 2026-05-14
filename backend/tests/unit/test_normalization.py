from app.services.normalization import normalize_comment_text


def test_normalize_comment_text_removes_urls_mentions_and_extra_spaces():
    value = normalize_comment_text("Hi @rootellect  see https://example.com   #MindCalm")

    assert value == "Hi see MindCalm"

