import re

X_TWEET_ID_RE = re.compile(r"^[0-9]{1,19}$")


def is_valid_x_tweet_id(tweet_id: str | None) -> bool:
    return bool(tweet_id and X_TWEET_ID_RE.match(tweet_id.strip()))


def normalize_x_tweet_id(tweet_id: str) -> str:
    cleaned = tweet_id.strip()
    if not is_valid_x_tweet_id(cleaned):
        raise ValueError(
            "X tweet ID must be a numeric post ID (1–19 digits), e.g. from the post URL."
        )
    return cleaned


def x_status_url(tweet_id: str, *, author_handle: str | None = None) -> str:
    """Public X status URL. Handle optional — /i/status/ works for all tiers."""
    tid = normalize_x_tweet_id(tweet_id)
    if author_handle:
        handle = author_handle.lstrip("@").strip()
        if handle:
            return f"https://x.com/{handle}/status/{tid}"
    return f"https://x.com/i/status/{tid}"


def compose_link_quote_tweet(text: str, tweet_id: str, *, author_handle: str | None = None) -> str:
    """Quote-style post using a status URL in text (works on all X API tiers)."""
    url = x_status_url(tweet_id, author_handle=author_handle)
    body = text.strip()
    separator = "\n\n"
    combined = f"{body}{separator}{url}"
    if len(combined) <= 280:
        return combined
    max_body = 280 - len(separator) - len(url) - 1
    if max_body < 1:
        return url[:280]
    trimmed = body[:max_body].rstrip()
    if len(trimmed) < len(body):
        trimmed = trimmed.rstrip(".,;:!?") + "…"
    return f"{trimmed}{separator}{url}"
