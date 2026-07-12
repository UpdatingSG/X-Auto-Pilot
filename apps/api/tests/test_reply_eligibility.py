from xautopilot.services.reply_eligibility_service import assess_reply_eligibility, humanize_x_reply_error


def test_assess_reply_eligibility_everyone():
    allowed, reason = assess_reply_eligibility(
        {"reply_settings": "everyone"},
        {"username": "rakyll"},
        "42",
    )
    assert allowed is True
    assert reason is None


def test_assess_reply_eligibility_following_blocks_when_not_following():
    allowed, reason = assess_reply_eligibility(
        {"reply_settings": "following"},
        {"username": "rakyll", "connection_status": []},
        "42",
    )
    assert allowed is False
    assert reason and "only allows replies from accounts they follow" in reason


def test_assess_reply_eligibility_following_allows_when_following():
    allowed, reason = assess_reply_eligibility(
        {"reply_settings": "following"},
        {"username": "rakyll", "connection_status": ["following"]},
        "42",
    )
    assert allowed is True
    assert reason is None


def test_assess_reply_eligibility_mentioned_users():
    allowed, reason = assess_reply_eligibility(
        {
            "reply_settings": "mentionedUsers",
            "entities": {"mentions": [{"id": "99"}]},
        },
        {"username": "rakyll"},
        "42",
    )
    assert allowed is False
    assert reason and "mentioned accounts" in reason


def test_humanize_x_reply_error():
    raw = (
        "Reply to this conversation is not allowed because you have not been mentioned "
        "or otherwise engaged by the author of the post you are replying to."
    )
    msg = humanize_x_reply_error(raw)
    assert "quote-tweet" in msg.lower()
