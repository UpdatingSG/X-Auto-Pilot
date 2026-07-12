"""Check whether the connected X account can reply to a tweet."""

from __future__ import annotations


def humanize_x_reply_error(message: str) -> str:
    lower = message.lower()
    if "not been mentioned" in lower or "conversation is not allowed" in lower:
        return (
            "X blocked this reply. The author only allows replies from accounts they follow "
            "or explicitly mention. Follow them on X, get mentioned in the post, or publish "
            "as a quote-tweet instead."
        )
    if "not allowed" in lower and "reply" in lower:
        return (
            "X blocked this reply because of the author's reply settings. "
            "Try a quote-tweet instead."
        )
    return message


def assess_reply_eligibility(
    tweet: dict,
    author_user: dict,
    viewer_x_user_id: str | None,
) -> tuple[bool, str | None]:
    """Return (allowed, block_reason). Unknown viewer => assume allowed (checked again at publish)."""
    if not viewer_x_user_id:
        return True, None

    settings = str(tweet.get("reply_settings") or "everyone").lower()
    handle = str(author_user.get("username") or "author")

    if settings in ("everyone", ""):
        return True, None

    connection = {str(c).lower() for c in (author_user.get("connection_status") or [])}

    if settings == "following":
        if "following" in connection:
            return True, None
        return False, (
            f"@{handle} only allows replies from accounts they follow. "
            "Follow them on X first, or use a quote-tweet instead."
        )

    if settings in ("mentionedusers", "mentioned_users"):
        mentions = tweet.get("entities", {}).get("mentions", []) or []
        mentioned_ids = {str(m.get("id")) for m in mentions if isinstance(m, dict) and m.get("id")}
        if viewer_x_user_id in mentioned_ids:
            return True, None
        return False, (
            f"@{handle} only allows replies from mentioned accounts. "
            "Quote-tweet instead if you still want to engage."
        )

    if settings == "subscribers":
        return False, f"@{handle} only allows replies from paid subscribers."

    if settings == "verified":
        return False, f"@{handle} only allows replies from verified accounts."

    return False, (
        f"@{handle} restricts who can reply ({settings}). Try a quote-tweet instead."
    )


def reply_meta_from_context(conversation_context) -> dict:
    if isinstance(conversation_context, dict):
        return conversation_context
    return {}
