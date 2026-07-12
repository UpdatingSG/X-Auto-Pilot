"""Check whether the connected X account can reply to a tweet."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReplyEligibilityResult:
    """Eligibility for replying. Prefer attempting publish unless confirmed_block is True."""

    can_attempt: bool = True
    warning: str | None = None
    confirmed_block: bool = False
    block_reason: str | None = None
    reply_settings: str | None = None


def is_x_reply_forbidden_error(message: str) -> bool:
    lower = message.lower()
    return (
        "not been mentioned" in lower
        or "conversation is not allowed" in lower
        or ("not allowed" in lower and "reply" in lower)
    )


def should_fallback_reply_to_quote(error_message: str) -> bool:
    """Quote-tweets are not subject to X reply restrictions."""
    if not error_message.strip():
        return True
    return is_x_reply_forbidden_error(error_message) or "403" in error_message


def humanize_x_reply_error(message: str, *, reply_settings: str | None = None) -> str:
    lower = message.lower()
    settings = str(reply_settings or "").lower()
    if "blocked the quote-tweet" in lower:
        return message
    if "not been mentioned" in lower or "conversation is not allowed" in lower:
        if settings in ("everyone", ""):
            return (
                "X blocked this reply even though the post allows open replies. "
                "Your X account is likely restricted from replying to others (anti-spam). "
                "We publish engagement drafts as quote-tweets instead."
            )
        return (
            "X blocked this reply. When the author limits replies, you can only reply if "
            "they follow you on X or @mention you in the post — not just because you follow them. "
            "Publishing as a quote-tweet instead usually works."
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
) -> ReplyEligibilityResult:
    """Assess reply eligibility based on X reply_settings and connection_status.

    Important: reply_settings ``following`` means only accounts the *author follows* may reply
    (connection_status ``followed_by``), NOT accounts that follow the author (``following``).
    """
    settings_raw = tweet.get("reply_settings")
    settings = str(settings_raw or "everyone").lower()
    handle = str(author_user.get("username") or "author")

    if settings in ("everyone", ""):
        return ReplyEligibilityResult(reply_settings=settings_raw)

    connection = {str(c).lower() for c in (author_user.get("connection_status") or [])}

    if settings == "following":
        # Author allows replies only from accounts they follow → author must follow the viewer.
        if "followed_by" in connection:
            return ReplyEligibilityResult(reply_settings=settings_raw)
        if not connection:
            return ReplyEligibilityResult(
                reply_settings=settings_raw,
                warning=(
                    f"@{handle} may only allow replies from accounts they follow. "
                    "They need to follow you on X — following them is not enough."
                ),
            )
        return ReplyEligibilityResult(
            reply_settings=settings_raw,
            confirmed_block=True,
            can_attempt=False,
            block_reason=(
                f"@{handle} only allows replies from accounts they follow. "
                "They don't follow you yet — ask for a follow-back or use a quote-tweet."
            ),
        )

    if settings in ("mentionedusers", "mentioned_users"):
        mentions = tweet.get("entities", {}).get("mentions", []) or []
        mentioned_ids = {str(m.get("id")) for m in mentions if isinstance(m, dict) and m.get("id")}
        if viewer_x_user_id and mentioned_ids and viewer_x_user_id in mentioned_ids:
            return ReplyEligibilityResult(reply_settings=settings_raw)
        if viewer_x_user_id and mentioned_ids and viewer_x_user_id not in mentioned_ids:
            return ReplyEligibilityResult(
                reply_settings=settings_raw,
                confirmed_block=True,
                can_attempt=False,
                block_reason=(
                    f"@{handle} only allows replies from mentioned accounts. "
                    "Quote-tweet instead if you still want to engage."
                ),
            )
        return ReplyEligibilityResult(
            reply_settings=settings_raw,
            warning=(
                f"@{handle} may only allow replies from mentioned accounts. "
                "Quote-tweet instead if publish fails."
            ),
        )

    if settings in ("subscribers", "verified"):
        return ReplyEligibilityResult(
            reply_settings=settings_raw,
            confirmed_block=True,
            can_attempt=False,
            block_reason=(
                f"@{handle} only allows replies from {settings} accounts. "
                "Use a quote-tweet instead."
            ),
        )

    return ReplyEligibilityResult(
        reply_settings=settings_raw,
        warning=f"@{handle} restricts who can reply ({settings}). Publish may fail.",
    )


def reply_meta_from_context(conversation_context) -> dict:
    if isinstance(conversation_context, dict):
        return conversation_context
    return {}


def discovered_tweet_is_safe_for_auto_reply(
    *,
    reply_block_confirmed: bool = False,
    reply_warning: str | None = None,
    reply_settings: str | None = None,
) -> bool:
    """Only auto-discover/draft when X is likely to accept the reply."""
    if reply_block_confirmed:
        return False
    settings = str(reply_settings or "").lower()
    if settings in ("everyone",):
        return True
    if not settings:
        return False
    if settings in ("following", "mentionedusers", "mentioned_users"):
        return reply_warning is None
    return False
