"""Unit tests for mixed plan slot logic."""

from datetime import date

from xautopilot.services.agents.content_planner import (
    PlannedIdea,
    _enforce_plan_composition,
    _parse_planned_ideas,
    plan_slot_counts,
    should_include_thread,
    thread_plan_days,
)


def test_two_threads_per_week_includes_monday_and_sunday():
    assert thread_plan_days(2) == [0, 6]


def test_sunday_is_thread_day():
    assert should_include_thread(date(2026, 7, 5), 2)  # Sunday


def test_wednesday_is_not_thread_day_for_two_per_week():
    assert not should_include_thread(date(2026, 7, 1), 2)  # Wednesday


def test_parse_planned_ideas_ignores_invalid_reply_target_uuid():
    data = {
        "ideas": [
            {
                "content_type": "tweet",
                "category": "engineering",
                "title": "One",
                "hook_idea": "h",
                "rationale": "r",
                "reply_target_id": "not-a-valid-uuid",
            },
            {
                "content_type": "tweet",
                "category": "engineering",
                "title": "Two",
                "hook_idea": "h",
                "rationale": "r",
            },
            {
                "content_type": "thread",
                "category": "educational",
                "title": "Three",
                "hook_idea": "h",
                "rationale": "r",
            },
        ]
    }
    ideas = _parse_planned_ideas(data, 3)
    assert ideas[0].reply_target_id is None


def test_enforce_plan_composition_overrides_llm_tweet_labels():
    llm_ideas = [
        PlannedIdea("tweet", "engineering", f"Idea {i}", "hook", "why") for i in range(4)
    ]
    targets = [{"id": "00000000-0000-0000-0000-000000000001", "author_handle": "naval", "tweet_text": "Hello"}]

    enforced = _enforce_plan_composition(
        llm_ideas,
        tweet_count=2,
        thread_count=1,
        reply_count=1,
        quote_count=0,
        reply_targets=targets,
    )

    assert [i.content_type for i in enforced] == ["tweet", "tweet", "thread", "reply"]
    assert enforced[-1].reply_target_id is not None


def test_sunday_slots_include_thread():
    slots = plan_slot_counts(
        date(2026, 7, 5),
        tweets_per_day=3,
        threads_per_week=2,
        replies_per_day=2,
        reply_target_count=0,
        growth_mode=False,
    )
    assert slots["thread_count"] == 1
    assert slots["tweet_count"] == 2
    assert slots["total"] == 3
