from xautopilot.services.learning_service import (
    _InsightAdjustments,
    _category_adjustments_from_posts,
    _weights_from_insights,
)


class _Metrics:
    def __init__(self, engagement_rate: float, bookmarks: int = 0, likes: int = 0):
        self.engagement_rate = engagement_rate
        self.bookmarks = bookmarks
        self.likes = likes


class _Post:
    def __init__(self, category: str, engagement_rate: float, content_type: str = "tweet"):
        self.category = category
        self.content_type = content_type
        self.preview_text = "What do you think?"
        self.metrics = _Metrics(engagement_rate)


def test_category_adjustments_from_posts():
    posts = [_Post("educational", 0.05), _Post("story", 0.01)]
    adj = _category_adjustments_from_posts(posts)
    assert adj["increase_weight"] == ["educational"]
    assert adj["decrease_weight"] == ["story"]


def test_weights_from_insights_builds_category_and_type_weights():
    insights = _InsightAdjustments({"increase_weight": ["educational"], "decrease_weight": ["story"]})
    posts = [
        _Post("educational", 0.08, "reply"),
        _Post("story", 0.01, "tweet"),
    ]
    weights = _weights_from_insights(insights, posts)
    assert weights["category_weights"]["educational"] == 1.25
    assert weights["category_weights"]["story"] == 0.75
    assert "reply" in weights["content_type_weights"]
