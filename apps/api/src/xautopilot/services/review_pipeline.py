from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ReviewResult:
    original_text: str
    humanized_text: str
    ai_detection_score: float
    fact_check_passed: bool
    issues: list[str] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.fact_check_passed and self.ai_detection_score < 0.2 and not self.issues


class AIDetector(Protocol):
    async def score(self, text: str) -> float: ...


class Humanizer(Protocol):
    async def humanize(self, text: str) -> str: ...


class FactChecker(Protocol):
    async def check(self, text: str, *, context: str | None = None) -> tuple[bool, list[str]]: ...


class MockAIDetector:
    def __init__(self, score: float = 0.1):
        self._score = score

    async def score(self, text: str) -> float:
        if "AS AN AI" in text.upper():
            return 0.9
        return self._score


class MockHumanizer:
    async def humanize(self, text: str) -> str:
        cleaned = text.replace("As an AI language model,", "").strip()
        return cleaned or text


class MockFactChecker:
    def __init__(self, *, pass_check: bool = True):
        self._pass = pass_check

    async def check(self, text: str, *, context: str | None = None) -> tuple[bool, list[str]]:
        if not self._pass:
            return False, ["Unsupported claim"]
        if "definitely invented statistic" in text.lower():
            return False, ["Unverified statistic"]
        return True, []


async def review_content(
    text: str,
    *,
    context: str | None = None,
    detector: AIDetector | None = None,
    humanizer: Humanizer | None = None,
    fact_checker: FactChecker | None = None,
    ai_threshold: float = 0.2,
) -> ReviewResult:
    """Fixed order: AI detection → humanize → fact check."""
    detector = detector or MockAIDetector()
    humanizer = humanizer or MockHumanizer()
    fact_checker = fact_checker or MockFactChecker()

    stages: list[str] = []
    issues: list[str] = []

    stages.append("ai_detection")
    ai_score = await detector.score(text)
    if ai_score >= ai_threshold:
        issues.append(f"AI detection score {ai_score:.2f} >= {ai_threshold:.2f}")

    stages.append("humanizer")
    humanized = await humanizer.humanize(text)

    stages.append("fact_checker")
    fact_ok, fact_issues = await fact_checker.check(humanized, context=context)
    issues.extend(fact_issues)

    return ReviewResult(
        original_text=text,
        humanized_text=humanized,
        ai_detection_score=ai_score,
        fact_check_passed=fact_ok,
        issues=issues,
        stages=stages,
    )
