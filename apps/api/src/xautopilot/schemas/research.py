from pydantic import BaseModel, Field


class ResearchRunRequest(BaseModel):
    topics: list[str] = Field(min_length=1, max_length=10)
    providers: list[str] = Field(
        default_factory=lambda: [
            "hacker_news",
            "github_trending",
            "devto",
            "reddit_browser",
            "x_browser",
        ]
    )
    limit_per_query: int = Field(default=10, ge=1, le=50)


class ResearchDiscussionResponse(BaseModel):
    provider: str
    external_id: str
    title: str
    url: str
    excerpt: str
    author: str | None = None
    score: float
    comment_count: int
    canonical_key: str


class ResearchInsightResponse(BaseModel):
    summary: str
    source_keys: list[str]


class ResearchReportResponse(BaseModel):
    run_date: str
    topics: list[str]
    discussions: list[ResearchDiscussionResponse]
    insights: list[ResearchInsightResponse]
    markdown: str
    providers_used: list[str]
