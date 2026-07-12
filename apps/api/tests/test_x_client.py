from xautopilot.services.x_client import LiveXClient


def test_parse_discovered_tweets_accepts_single_tweet_object():
    client = LiveXClient()
    payload = {
        "data": {
            "id": "1234567890123456789",
            "author_id": "42",
            "text": "Hello from a single tweet lookup",
            "public_metrics": {"like_count": 7},
        },
        "includes": {
            "users": [
                {
                    "id": "42",
                    "username": "rakyll",
                    "public_metrics": {"followers_count": 120_000},
                }
            ]
        },
    }

    tweets = client._parse_discovered_tweets(payload)

    assert len(tweets) == 1
    assert tweets[0].x_tweet_id == "1234567890123456789"
    assert tweets[0].author_handle == "rakyll"
    assert tweets[0].tweet_text == "Hello from a single tweet lookup"
    assert tweets[0].likes == 7


def test_parse_discovered_tweets_accepts_tweet_list():
    client = LiveXClient()
    payload = {
        "data": [
            {
                "id": "111",
                "author_id": "9",
                "text": "First",
                "public_metrics": {"like_count": 1},
            }
        ],
        "includes": {"users": [{"id": "9", "username": "swyx", "public_metrics": {}}]},
    }

    tweets = client._parse_discovered_tweets(payload)

    assert len(tweets) == 1
    assert tweets[0].author_handle == "swyx"
