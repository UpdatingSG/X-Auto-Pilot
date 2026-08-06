import pytest

from xautopilot.services.review_pipeline import (
    MockAIDetector,
    MockFactChecker,
    MockHumanizer,
    review_content,
)


@pytest.mark.asyncio
async def test_review_pipeline_stage_order_and_pass():
    result = await review_content(
        "A crisp technical take on retries.",
        detector=MockAIDetector(score=0.05),
        humanizer=MockHumanizer(),
        fact_checker=MockFactChecker(pass_check=True),
    )
    assert result.stages == ["ai_detection", "humanizer", "fact_checker"]
    assert result.passed is True
    assert result.issues == []


@pytest.mark.asyncio
async def test_review_fails_on_high_ai_score_but_still_humanizes():
    result = await review_content(
        "As an AI language model, here is a thread.",
        detector=MockAIDetector(),
        humanizer=MockHumanizer(),
        fact_checker=MockFactChecker(pass_check=True),
    )
    assert result.passed is False
    assert result.ai_detection_score >= 0.2
    assert "As an AI language model," not in result.humanized_text
    assert result.issues


@pytest.mark.asyncio
async def test_review_fails_on_fact_check():
    result = await review_content(
        "This cites a definitely invented statistic.",
        detector=MockAIDetector(score=0.01),
        fact_checker=MockFactChecker(pass_check=True),
    )
    assert result.passed is False
    assert result.fact_check_passed is False
