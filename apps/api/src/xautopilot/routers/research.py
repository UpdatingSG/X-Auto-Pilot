from fastapi import APIRouter, Depends, HTTPException, status

from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.research import ResearchReportResponse, ResearchRunRequest
from xautopilot.services.providers.registry import get_provider
from xautopilot.services.research_engine import run_daily_research

router = APIRouter(prefix="/v1/research", tags=["research"])


@router.post("/run", response_model=ResearchReportResponse)
async def run_research(
    data: ResearchRunRequest,
    current_user: User = Depends(get_current_user),
):
    """Run multi-provider research (fixture/mock backends in Phase 1)."""
    _ = current_user
    providers = []
    for name in data.providers:
        try:
            providers.append(get_provider(name))
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from None

    if not providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid provider is required",
        )

    report = await run_daily_research(
        topics=data.topics,
        providers=providers,
        limit_per_query=data.limit_per_query,
    )
    return ResearchReportResponse(
        run_date=report.run_date.isoformat(),
        topics=report.topics,
        discussions=[
            {
                "provider": d.provider,
                "external_id": d.external_id,
                "title": d.title,
                "url": d.url,
                "excerpt": d.excerpt,
                "author": d.author,
                "score": d.score,
                "comment_count": d.comment_count,
                "canonical_key": d.canonical_key,
            }
            for d in report.discussions
        ],
        insights=[
            {"summary": i.summary, "source_keys": i.source_keys} for i in report.insights
        ],
        markdown=report.markdown,
        providers_used=[p.name for p in providers],
    )
