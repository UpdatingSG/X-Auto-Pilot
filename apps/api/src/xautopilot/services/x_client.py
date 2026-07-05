import random
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from xautopilot.config import settings


@dataclass
class TweetPostResult:
    x_tweet_id: str


@dataclass
class ThreadPostResult:
    x_tweet_id: str
    thread_ids: list[str]


@dataclass
class TweetMetricsResult:
    impressions: int
    likes: int
    replies: int
    reposts: int
    bookmarks: int
    quotes: int
    follower_count: int | None = None


class XApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class XApiUnauthorizedError(XApiError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class XApiRateLimitError(XApiError):
    def __init__(self, message: str = "Rate limited", *, retry_after_seconds: int | None = None):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message, status_code=429)


class XClient(Protocol):
    async def post_tweet(self, access_token: str, text: str) -> TweetPostResult: ...

    async def post_reply(
        self, access_token: str, text: str, *, in_reply_to_tweet_id: str
    ) -> TweetPostResult: ...

    async def post_thread(self, access_token: str, tweets: list[str]) -> ThreadPostResult: ...

    async def get_tweet_metrics(self, access_token: str, x_tweet_id: str) -> TweetMetricsResult: ...


def _retry_after_seconds(response: httpx.Response) -> int | None:
    retry_after = response.headers.get("retry-after")
    if retry_after and retry_after.isdigit():
        return int(retry_after)
    reset = response.headers.get("x-rate-limit-reset")
    if reset and reset.isdigit():
        return max(0, int(reset) - int(time.time()))
    return None


def _x_api_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body.get("errors"), list) and body["errors"]:
            first = body["errors"][0]
            if isinstance(first, dict):
                return first.get("detail") or first.get("title") or str(first)
        if body.get("detail"):
            return str(body["detail"])
        if body.get("title"):
            return str(body.get("detail") or body["title"])
        if body.get("error_description"):
            return str(body["error_description"])
        if body.get("error"):
            return str(body["error"])
    except Exception:
        pass
    text = (response.text or "").strip()
    return text or f"X API error ({response.status_code})"


async def _live_request(
    method: str,
    url: str,
    access_token: str,
    **kwargs,
) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, headers=headers, **kwargs)
    if response.status_code == 401:
        raise XApiUnauthorizedError(_x_api_error_message(response))
    if response.status_code == 429:
        raise XApiRateLimitError(
            _x_api_error_message(response),
            retry_after_seconds=_retry_after_seconds(response),
        )
    if response.status_code >= 400:
        raise XApiError(_x_api_error_message(response), status_code=response.status_code)
    return response


class MockXClient:
    """Records posts in-memory; used when X_API_MODE=mock."""

    def __init__(self) -> None:
        self.posts: list[dict[str, str]] = []

    async def post_tweet(self, access_token: str, text: str) -> TweetPostResult:
        tweet_id = str(random.randint(1_000_000_000, 9_999_999_999))
        self.posts.append({"access_token": access_token, "text": text, "x_tweet_id": tweet_id})
        return TweetPostResult(x_tweet_id=tweet_id)

    async def post_reply(
        self, access_token: str, text: str, *, in_reply_to_tweet_id: str
    ) -> TweetPostResult:
        tweet_id = str(random.randint(1_000_000_000, 9_999_999_999))
        self.posts.append(
            {
                "access_token": access_token,
                "text": text,
                "x_tweet_id": tweet_id,
                "in_reply_to_tweet_id": in_reply_to_tweet_id,
            }
        )
        return TweetPostResult(x_tweet_id=tweet_id)

    async def post_thread(self, access_token: str, tweets: list[str]) -> ThreadPostResult:
        ids: list[str] = []
        for i, text in enumerate(tweets):
            tweet_id = str(random.randint(1_000_000_000, 9_999_999_999))
            entry: dict[str, str] = {"access_token": access_token, "text": text, "x_tweet_id": tweet_id}
            if i > 0:
                entry["in_reply_to_tweet_id"] = ids[-1]
            self.posts.append(entry)
            ids.append(tweet_id)
        return ThreadPostResult(x_tweet_id=ids[0], thread_ids=ids)

    async def get_tweet_metrics(self, access_token: str, x_tweet_id: str) -> TweetMetricsResult:
        seed = int(x_tweet_id[-6:]) if x_tweet_id[-6:].isdigit() else 42
        impressions = 1000 + seed % 4000
        likes = 10 + seed % 40
        replies = 2 + seed % 8
        reposts = 1 + seed % 5
        bookmarks = 3 + seed % 10
        quotes = seed % 3
        return TweetMetricsResult(
            impressions=impressions,
            likes=likes,
            replies=replies,
            reposts=reposts,
            bookmarks=bookmarks,
            quotes=quotes,
            follower_count=500 + seed % 200,
        )


class LiveXClient:
    async def post_tweet(self, access_token: str, text: str) -> TweetPostResult:
        response = await _live_request(
            "POST",
            f"{settings.x_api_base_url}/tweets",
            access_token,
            json={"text": text},
        )
        data = response.json()["data"]
        return TweetPostResult(x_tweet_id=data["id"])

    async def post_reply(
        self, access_token: str, text: str, *, in_reply_to_tweet_id: str
    ) -> TweetPostResult:
        response = await _live_request(
            "POST",
            f"{settings.x_api_base_url}/tweets",
            access_token,
            json={"text": text, "reply": {"in_reply_to_tweet_id": in_reply_to_tweet_id}},
        )
        data = response.json()["data"]
        return TweetPostResult(x_tweet_id=data["id"])

    async def post_thread(self, access_token: str, tweets: list[str]) -> ThreadPostResult:
        ids: list[str] = []
        for i, text in enumerate(tweets):
            payload: dict = {"text": text}
            if i > 0:
                payload["reply"] = {"in_reply_to_tweet_id": ids[-1]}
            response = await _live_request(
                "POST",
                f"{settings.x_api_base_url}/tweets",
                access_token,
                json=payload,
            )
            tweet_id = response.json()["data"]["id"]
            ids.append(tweet_id)
        return ThreadPostResult(x_tweet_id=ids[0], thread_ids=ids)

    async def get_tweet_metrics(self, access_token: str, x_tweet_id: str) -> TweetMetricsResult:
        response = await _live_request(
            "GET",
            f"{settings.x_api_base_url}/tweets/{x_tweet_id}",
            access_token,
            params={"tweet.fields": "public_metrics"},
        )
        metrics = response.json()["data"]["public_metrics"]
        return TweetMetricsResult(
            impressions=metrics.get("impression_count", 0),
            likes=metrics.get("like_count", 0),
            replies=metrics.get("reply_count", 0),
            reposts=metrics.get("retweet_count", 0),
            bookmarks=metrics.get("bookmark_count", 0),
            quotes=metrics.get("quote_count", 0),
        )


mock_x_client = MockXClient()


def get_x_client() -> XClient:
    if settings.x_api_mode == "mock":
        return mock_x_client
    return LiveXClient()
