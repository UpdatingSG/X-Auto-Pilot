from xautopilot.services.reply_eligibility_service import (
    assess_reply_eligibility,
    discovered_tweet_is_safe_for_auto_reply,
    humanize_x_reply_error,
    should_fallback_reply_to_quote,
)


def test_assess_reply_eligibility_everyone():
    result = assess_reply_eligibility(
        {"reply_settings": "everyone"},
        {"username": "rakyll"},
        "42",
    )
    assert result.can_attempt is True
    assert result.confirmed_block is False


def test_following_allows_when_author_follows_viewer():
    result = assess_reply_eligibility(
        {"reply_settings": "following"},
        {"username": "rakyll", "connection_status": ["followed_by"]},
        "42",
    )
    assert result.can_attempt is True
    assert result.confirmed_block is False


def test_following_blocks_when_viewer_follows_author_but_author_does_not_follow_back():
    """Common mistake: you follow them, but reply_settings=following needs them to follow you."""
    result = assess_reply_eligibility(
        {"reply_settings": "following"},
        {"username": "rakyll", "connection_status": ["following"]},
        "42",
    )
    assert result.confirmed_block is True
    assert result.can_attempt is False
    assert "don't follow you" in (result.block_reason or "").lower()


def test_following_unknown_connection_warns_not_blocks():
    result = assess_reply_eligibility(
        {"reply_settings": "following"},
        {"username": "rakyll", "connection_status": []},
        "42",
    )
    assert result.can_attempt is True
    assert result.confirmed_block is False
    assert result.warning


def test_mentioned_users_blocks_when_not_mentioned():
    result = assess_reply_eligibility(
        {
            "reply_settings": "mentionedUsers",
            "entities": {"mentions": [{"id": "99"}]},
        },
        {"username": "rakyll"},
        "42",
    )
    assert result.confirmed_block is True


def test_discovered_tweet_is_safe_for_auto_reply():
    assert discovered_tweet_is_safe_for_auto_reply(reply_settings="everyone") is True
    assert discovered_tweet_is_safe_for_auto_reply(reply_settings="following", reply_warning="maybe") is False
    assert discovered_tweet_is_safe_for_auto_reply(reply_settings="following") is True
    assert discovered_tweet_is_safe_for_auto_reply(reply_block_confirmed=True, reply_settings="everyone") is False


def test_humanize_x_reply_error():
    raw = (
        "Reply to this conversation is not allowed because you have not been mentioned "
        "or otherwise engaged by the author of the post you are replying to."
    )
    msg = humanize_x_reply_error(raw, reply_settings="following")
    assert "follow you" in msg.lower()
    assert "you follow them" not in msg.lower() or "not just because you follow" in msg.lower()

    account_msg = humanize_x_reply_error(raw, reply_settings="everyone")
    assert "anti-spam" in account_msg.lower() or "open replies" in account_msg.lower()


def test_should_fallback_reply_to_quote():
    raw = (
        "Reply to this conversation is not allowed because you have not been mentioned "
        "or otherwise engaged by the author of the post you are replying to."
    )
    assert should_fallback_reply_to_quote(raw) is True
    assert should_fallback_reply_to_quote("You are not permitted to create a Tweet") is False
