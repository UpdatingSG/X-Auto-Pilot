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


@dataclass
class DiscoveredTweet:
    x_tweet_id: str
    x_user_id: str
    author_handle: str
    tweet_text: str
    author_followers: int
    likes: int
    relevance_score: float = 0.0


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

    async def post_quote_tweet(
        self, access_token: str, text: str, *, quote_tweet_id: str
    ) -> TweetPostResult: ...

    async def post_thread(self, access_token: str, tweets: list[str]) -> ThreadPostResult: ...

    async def get_tweet_metrics(self, access_token: str, x_tweet_id: str) -> TweetMetricsResult: ...

    async def search_recent_tweets(
        self, access_token: str, *, query: str, max_results: int = 10
    ) -> list[DiscoveredTweet]: ...

    async def get_user_recent_tweets(
        self, access_token: str, username: str, *, max_results: int = 5
    ) -> list[DiscoveredTweet]: ...

    async def lookup_tweet(self, access_token: str, tweet_id: str) -> DiscoveredTweet: ...


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

    async def post_quote_tweet(
        self, access_token: str, text: str, *, quote_tweet_id: str
    ) -> TweetPostResult:
        tweet_id = str(random.randint(1_000_000_000, 9_999_999_999))
        self.posts.append(
            {
                "access_token": access_token,
                "text": text,
                "x_tweet_id": tweet_id,
                "quote_tweet_id": quote_tweet_id,
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

    async def search_recent_tweets(
        self, access_token: str, *, query: str, max_results: int = 10
    ) -> list[DiscoveredTweet]:
        del access_token, query
        return [
            DiscoveredTweet(
                x_tweet_id="9000000000000000010",
                x_user_id="2001",
                author_handle="rakyll",
                tweet_text="Hot take: most teams adopt microservices before they need them. What's your threshold for splitting a service?",
                author_followers=120_000,
                likes=42,
                relevance_score=0.9,
            )
        ][:max_results]

    async def get_user_recent_tweets(
        self, access_token: str, username: str, *, max_results: int = 5
    ) -> list[DiscoveredTweet]:
        del access_token
        return [
            DiscoveredTweet(
                x_tweet_id=f"80000000000000000{idx}",
                x_user_id=f"3{idx}",
                author_handle=username,
                tweet_text=f"Recent post from @{username} about backend systems and AI engineering #{idx}",
                author_followers=75_000 + idx * 5_000,
                likes=10 + idx * 3,
                relevance_score=0.75,
            )
            for idx in range(max_results)
        ]

    async def lookup_tweet(self, access_token: str, tweet_id: str) -> DiscoveredTweet:
        del access_token
        return DiscoveredTweet(
            x_tweet_id=tweet_id,
            x_user_id="mock-user",
            author_handle="example",
            tweet_text="Mock tweet text loaded from URL.",
            author_followers=50_000,
            likes=8,
            relevance_score=0.8,
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

    async def post_quote_tweet(
        self, access_token: str, text: str, *, quote_tweet_id: str
    ) -> TweetPostResult:
        response = await _live_request(
            "POST",
            f"{settings.x_api_base_url}/tweets",
            access_token,
            json={"text": text, "quote_tweet_id": quote_tweet_id},
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
            params={
                "tweet.fields": "public_metrics,non_public_metrics,organic_metrics",
            },
        )
        data = response.json()["data"]
        public = data.get("public_metrics") or {}
        non_public = data.get("non_public_metrics") or {}
        organic = data.get("organic_metrics") or {}

        impressions = (
            non_public.get("impression_count")
            or organic.get("impression_count")
            or public.get("impression_count")
            or 0
        )
        likes = organic.get("like_count") or public.get("like_count", 0)
        replies = organic.get("reply_count") or public.get("reply_count", 0)
        reposts = organic.get("retweet_count") or public.get("retweet_count", 0)
        bookmarks = public.get("bookmark_count", 0)
        quotes = organic.get("quote_count") or public.get("quote_count", 0)

        return TweetMetricsResult(
            impressions=impressions,
            likes=likes,
            replies=replies,
            reposts=reposts,
            bookmarks=bookmarks,
            quotes=quotes,
        )

    def _parse_discovered_tweets(self, payload: dict) -> list[DiscoveredTweet]:
        tweets = payload.get("data") or []
        users = {
            user["id"]: user
            for user in (payload.get("includes") or {}).get("users") or []
        }
        discovered: list[DiscoveredTweet] = []
        for tweet in tweets:
            author = users.get(tweet.get("author_id"), {})
            metrics = tweet.get("public_metrics") or {}
            username = author.get("username") or "unknown"
            user_metrics = author.get("public_metrics") or {}
            discovered.append(
                DiscoveredTweet(
                    x_tweet_id=str(tweet["id"]),
                    x_user_id=str(tweet.get("author_id") or "unknown"),
                    author_handle=username,
                    tweet_text=str(tweet.get("text") or ""),
                    author_followers=int(user_metrics.get("followers_count") or 0),
                    likes=int(metrics.get("like_count") or 0),
                )
            )
        return discovered

    async def search_recent_tweets(
        self, access_token: str, *, query: str, max_results: int = 10
    ) -> list[DiscoveredTweet]:
        response = await _live_request(
            "GET",
            f"{settings.x_api_base_url}/tweets/search/recent",
            access_token,
            params={
                "query": query,
                "max_results": max(10, min(max_results, 100)),
                "tweet.fields": "author_id,created_at,public_metrics,text",
                "expansions": "author_id",
                "user.fields": "username,public_metrics",
            },
        )
        return self._parse_discovered_tweets(response.json())

    async def get_user_recent_tweets(
        self, access_token: str, username: str, *, max_results: int = 5
    ) -> list[DiscoveredTweet]:
        user_response = await _live_request(
            "GET",
            f"{settings.x_api_base_url}/users/by/username/{username.lstrip('@')}",
            access_token,
            params={"user.fields": "public_metrics"},
        )
        user = user_response.json()["data"]
        tweets_response = await _live_request(
            "GET",
            f"{settings.x_api_base_url}/users/{user['id']}/tweets",
            access_token,
            params={
                "max_results": max(5, min(max_results, 10)),
                "exclude": "retweets,replies",
                "tweet.fields": "author_id,created_at,public_metrics,text",
                "expansions": "author_id",
                "user.fields": "username,public_metrics",
            },
        )
        discovered = self._parse_discovered_tweets(tweets_response.json())
        followers = int((user.get("public_metrics") or {}).get("followers_count") or 0)
        for tweet in discovered:
            if tweet.author_followers <= 0:
                tweet.author_followers = followers
        return discovered

    async def lookup_tweet(self, access_token: str, tweet_id: str) -> DiscoveredTweet:
        response = await _live_request(
            "GET",
            f"{settings.x_api_base_url}/tweets/{tweet_id}",
            access_token,
            params={
                "tweet.fields": "author_id,created_at,public_metrics,text",
                "expansions": "author_id",
                "user.fields": "username,public_metrics",
            },
        )
        tweets = self._parse_discovered_tweets(response.json())
        if not tweets:
            raise XApiError("Tweet not found", status_code=404)
        return tweets[0]


mock_x_client = MockXClient()


def get_x_client() -> XClient:
    if settings.x_api_mode == "mock":
        return mock_x_client
    return LiveXClient()
