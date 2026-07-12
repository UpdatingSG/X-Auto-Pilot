from xautopilot.services.x_tweet_id import compose_link_quote_tweet, x_status_url


def test_x_status_url_with_handle():
    assert x_status_url("12345", author_handle="@alice") == "https://x.com/alice/status/12345"


def test_x_status_url_without_handle():
    assert x_status_url("12345") == "https://x.com/i/status/12345"


def test_compose_link_quote_tweet_fits_limit():
    text = compose_link_quote_tweet("Great thread", "12345", author_handle="bob")
    assert len(text) <= 280
    assert "https://x.com/bob/status/12345" in text
    assert text.startswith("Great thread")
