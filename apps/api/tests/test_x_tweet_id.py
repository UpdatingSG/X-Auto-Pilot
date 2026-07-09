"""Tests for X tweet ID validation."""

import pytest

from xautopilot.services.x_tweet_id import is_valid_x_tweet_id, normalize_x_tweet_id


def test_valid_tweet_ids():
    assert is_valid_x_tweet_id("2075248386043986155")
    assert is_valid_x_tweet_id("1234567890")


def test_invalid_tweet_ids():
    assert not is_valid_x_tweet_id("manual-Vivek4real_-77")
    assert not is_valid_x_tweet_id("")
    assert not is_valid_x_tweet_id("abc123")


def test_normalize_rejects_manual_placeholder():
    with pytest.raises(ValueError, match="numeric"):
        normalize_x_tweet_id("manual-handle-42")
