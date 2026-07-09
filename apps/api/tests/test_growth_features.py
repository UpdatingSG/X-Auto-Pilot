"""Tests for growth-mode content planning."""

from datetime import date

from xautopilot.services.agents.content_planner import plan_slot_counts


def test_growth_mode_allows_many_replies():
    slots = plan_slot_counts(
        date(2026, 7, 9),
        tweets_per_day=3,
        threads_per_week=1,
        replies_per_day=10,
        reply_target_count=8,
        growth_mode=True,
    )
    assert slots["tweet_count"] == 1
    assert slots["reply_count"] == 8
    assert slots["thread_count"] == 0


def test_balanced_mode_caps_replies_at_three():
    slots = plan_slot_counts(
        date(2026, 7, 9),
        tweets_per_day=3,
        threads_per_week=1,
        replies_per_day=10,
        reply_target_count=8,
        growth_mode=False,
    )
    assert slots["reply_count"] == 3
    assert slots["quote_count"] == 0


def test_growth_mode_includes_quote_slots():
    slots = plan_slot_counts(
        date(2026, 7, 9),
        tweets_per_day=1,
        threads_per_week=0,
        replies_per_day=5,
        reply_target_count=2,
        growth_mode=True,
        quote_tweets_per_day=2,
        quote_target_count=2,
    )
    assert slots["quote_count"] == 2
    assert slots["total"] == 5
