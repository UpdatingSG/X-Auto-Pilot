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
